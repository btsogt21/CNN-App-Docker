# Importing celery
from celery import Celery
from celery.contrib.abortable import AbortableTask

# Importing redis
import redis

# Model building and training imports
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Local imports
from loggingConfig import configure_logging

# Other imports:
import signal
import sys
import json
import os
import logging
import numpy as np

# Configure Logging
configure_logging()
logger = logging.getLogger(__name__)

# Environment Variables
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Creating a celery instance and a redis client. The Celery instance is used to create a task that will
# train the model, whereas the redis client is used to publish updates to the frontend. The redis client
# here is synchronous, as opposed to the asynchronous redis client used in the backend/app.py file.
# We can use a synchronous client here because the worker.py file is not an ASGI application and does
# not need to handle multiple concurrent connections.
# celery = Celery('task', broker='redis://redis:6379/0', backend='redis://redis:6379/0')
# broker parameter is used to specify the message broker url that celery uses to send and receive
# messages regarding task execution. The above specifies that the broker is a Redis instance running
# on the host 'redis' and port 6379.
# the backend parameter is used to specify the result backend url that celery uses to store task results
# and states. The above specifies that the backend is a Redis instance running on the host 'redis'
# and port 6379.
# 'task' is the name of the current module. The first argument to Celery() is always the name of the
# application module, and this one in specific is used to organize and reference tasks. 
# The broker and backend parameters are optional, but they are used here to specify
# the Redis instance that will be used for message passing and storing task results. We had it previously
# when we were using Redis to publish updates to the frontend.
redis_client = redis.Redis.from_url(REDIS_URL)
celery = Celery('tasks', backend=CELERY_RESULT_BACKEND, broker=CELERY_BROKER_URL)

# Handling the closing of the celery worker when a SIGINT or SIGTERM signal is received.
def handle_exit(signal, frame):
    logger.info('Received exit signal, shutting down...')
    celery.control.shutdown()  # Gracefully shutdown the Celery worker
    sys.exit(0)

# Associate the handle_exit function with the SIGINT and SIGTERM signals.
def setup_signal_handlers():
    signal.signal(signal.SIGINT, handle_exit)  # Handle Ctrl + C
    signal.signal(signal.SIGTERM, handle_exit)  # Handle termination signal


@celery.task(bind=True, base = AbortableTask)
def train_model(self, layers, units, epochs, batch_size, optimizer):
    try:
        logger.info(f"Training model with layers={layers}, units={units}, epochs={epochs}, batch_size={batch_size}, optimizer={optimizer}")
        #Loading CIFAR-10 in and splitting dataset
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()

        #Normalizing pixel values
        x_train, x_test = x_train/255.0, x_test/255.0

        #Mean subtraction
        mean = np.mean(x_train, axis = (0, 1, 2) )
        x_train = x_train - mean
        x_test = x_test - mean

        #Extracting validation set
        x_train, x_val, y_train, y_val = train_test_split(x_train, y_train, test_size = 0.1, stratify = y_train)

        #Data augmentation via shifts and horizontal flips

        datagen = ImageDataGenerator(
            width_shift_range = 0.1,
            height_shift_range = 0.1,
            horizontal_flip = True
        )

        datagen.fit(x_train)

        train_generator = datagen.flow(x_train, y_train, batch_size = batch_size)
        val_generator = tf.data.Dataset.from_tensor_slices((x_val, y_val)).batch(batch_size)
        test_generator = tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(batch_size)

        # Build model
        model = Sequential()
        model.add(Conv2D(units[0], (3, 3), activation='relu', input_shape=(32, 32, 3)))
        model.add(MaxPooling2D((2, 2)))
        for i in range(1, layers):
            model.add(Conv2D(units[i], (3, 3), activation='relu'))
            model.add(MaxPooling2D((2, 2)))
        model.add(Flatten())
        model.add(Dense(units[-1], activation = 'relu'))
        model.add(Dropout(0.5))
        model.add(Dense(10, activation='softmax'))

        logger.info("Model Summary:")
        model.summary()

        # Compile the model
        model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        logger.info("Final Training Parameters:")
        logger.info(f"Layers: {model.layers}")
        logger.info(f"Units: {[layer.filters if isinstance(layer, Conv2D) else layer.units for layer in model.layers if isinstance(layer, (Conv2D, Dense))]}")
        logger.info(f"Epochs: {epochs}")
        logger.info(f"Batch Size: {batch_size}")
        logger.info(f"Optimizer: {model.optimizer}")

        # Define a custom callback to track the training progress.
        # Note: Turns out the default output from tensorflow averages training accuracy and loss over 
        # the batches that we've already processed in a given
        # epoch, whereas the callback prints the accuracy and loss for the most recent batch.
        class TrainingCallback(tf.keras.callbacks.Callback):
            def __init__(self):
                super().__init__()
                self.batch_accuracies = []

            def on_epoch_end(self, epoch, logs=None):
                logs = logs or {}
                logger.info (f" Epoch {epoch + 1}: logs={logs}")
                update = {'status': "PROGRESS", 'epoch': epoch + 1, 'logs': logs}
                redis_client.publish('model_updates', json.dumps(update))

            def get_total_accuracy(self):
                return np.sum(self.batch_accuracies)
        
        model.fit(
            train_generator,
            epochs=epochs,
            validation_data=val_generator,
            callbacks=[TrainingCallback()],

        )

        # Evaluate the model on the test set
        test_loss, test_accuracy = model.evaluate(test_generator)
        response = {"status": "SUCCESS", 'test_accuracy': float(test_accuracy), 'test_loss': (test_loss)}
        redis_client.publish('model_updates', json.dumps(response))
    except Exception as e:
        logger.error(f"An error occurred during training.{e}")
        response = {"status": "ERROR", "message": str(e)}
        redis_client.publish('model_updates', json.dumps(response))
        raise

if __name__ == '__main__':
    setup_signal_handlers()
    celery.worker_main()