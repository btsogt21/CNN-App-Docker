# META

# Currently 1 active print statement as part of callback


# importing celery
from celery import Celery
import redis

# preprocessing imports
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import numpy as np

# model building and training imports
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# asyncio and aiohttp
import asyncio
import aiohttp

import json

# Creating a celery instance and a redis client. The Celery instance is used to create a task that will
# train the model, whereas the redis client is used to publish updates to the frontend. The redis client
# here is synchronous, as opposed to the asynchronous redis client used in the backend/app.py file.
# We can use a synchronous client here because the worker.py file is not an ASGI application and does
# not need to handle multiple concurrent connections.
celery = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')
redis_client = redis.Redis(host='redis', port = 6379, db = 0)

@celery.task(bind=True)
def train_model(self, layers, units, epochs, batch_size, optimizer):
    print(f"Training model with layers={layers}, units={units}, epochs={epochs}, batch_size={batch_size}, optimizer={optimizer}")
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

    print("Model Summary:")
    model.summary()

    # Compile the model
    model.compile(
        optimizer=optimizer,
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    print("Final Training Parameters:")
    print(f"Layers: {model.layers}")
    print(f"Units: {[layer.filters if isinstance(layer, Conv2D) else layer.units for layer in model.layers if isinstance(layer, (Conv2D, Dense))]}")
    print(f"Epochs: {epochs}")
    print(f"Batch Size: {batch_size}")
    print(f"Optimizer: {model.optimizer}")

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
            print (f" Epoch {epoch + 1}: logs={logs}")
            update = {'status': "PROGRESS", 'epoch': epoch + 1, 'logs': logs}
            redis_client.publish('model_updates', json.dumps(update))

        def get_total_accuracy(self):
            return np.sum(self.batch_accuracies)
    
    history = model.fit(
        train_generator,
        epochs=epochs,
        validation_data=val_generator,
        callbacks=[TrainingCallback()],

    )

    # Evaluate the model on the test set
    test_loss, test_accuracy = model.evaluate(test_generator)
    response = {"status": "SUCCESS", 'test_accuracy': test_accuracy, 'test_loss': test_loss}
    redis_client.publish('model_updates', json.dumps(response))
