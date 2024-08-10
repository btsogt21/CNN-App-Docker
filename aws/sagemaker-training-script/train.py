import os
import numpy as np
import tensorflow as tf
import boto3
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import logging
import redis
import json
from watchtower import CloudWatchLogHandler

#Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
# MODEL_DIR = os.getenv("SM_MODEL_DIR")
# TRAINING_DIR = os.getenv("SM_CHANNEL_TRAINING")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis.cifar-10-discovery:6379")

layers = int(os.getenv("SM_HP_layers"))
units = list(map(int, os.getenv("SM_HP_units").split(',')))
epochs = int(os.getenv("SM_HP_epochs"))
batch_size = int(os.getenv("SM_HP_batch_size"))
optimizer = os.getenv("SM_HP_optimizer")


# S3 Configuration
s3 = boto3.client("s3")
bucket_name = os.getenv("BUCKET_NAME")
prefix = 'cifar-10'

# Setting up redis client
redis_client = redis.Redis.from_url(REDIS_URL)

# Loading and preprocessing the data
def load_data_from_s3(file_key):
    local_path = '/tmp/' + file_key
    s3.download_file(bucket_name, f"{prefix}/{file_key}", local_path)
    return np.load(local_path)

def upload_data_to_s3(file_key, local_path):
    s3.upload_file(local_path, bucket_name, f"{prefix}/{file_key}")

def check_s3_data():
    try:
        s3.head_object(Bucket = bucket_name, Key = f"{prefix}/x_train.npy")
        s3.head_object(Bucket = bucket_name, Key = f"{prefix}/y_train.npy")
        s3.head_object(Bucket = bucket_name, Key = f"{prefix}/x_test.npy")
        s3.head_object(Bucket = bucket_name, Key = f"{prefix}/y_test.npy")
        return True
    except:
        return False

def save_data_to_local():
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
    np.save('/tmp/x_train.npy', x_train)
    np.save('/tmp/y_train.npy', y_train)
    np.save('/tmp/x_test.npy', x_test)
    np.save('/tmp/y_test.npy', y_test)
    return '/tmp/x_train.npy', '/tmp/y_train.npy', '/tmp/x_test.npy', '/tmp/y_test.npy'

def ensure_data():
    if not check_s3_data():
        x_train, y_train, x_test, y_test = save_data_to_local()
        upload_data_to_s3('x_train.npy', x_train)
        upload_data_to_s3('y_train.npy', y_train)
        upload_data_to_s3('x_test.npy', x_test)
        upload_data_to_s3('y_test.npy', y_test)
    else:
        logger.info("CIFAR-10 data already exists in S3, proceeding to load data")

ensure_data()

x_train = load_data_from_s3('x_train.npy')
y_train = load_data_from_s3('y_train.npy')
x_test = load_data_from_s3('x_test.npy')
y_test = load_data_from_s3('y_test.npy')

# Normalize pixel values
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