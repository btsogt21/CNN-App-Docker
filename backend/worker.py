# importing celery
from celery import Celery

# preprocessing imports
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import numpy as np

# model building and training imports
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator

celery = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery.task(bind=True)
def train_model(self, layers, units, epochs, batch_size, optimizer):
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
    # model = Sequential([
    #     Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 3)),
    #     MaxPooling2D((2, 2)),
    #     Conv2D(64, (3, 3), activation='relu'),
    #     MaxPooling2D((2, 2)),
    #     Conv2D(128, (3, 3), activation='relu'),
    #     Flatten(),
    #     Dense(128, activation='relu'),
    #     Dropout(0.5),
    #     Dense(10, activation='softmax')
    # ])

    # Compile the model
    model.compile(
        optimizer=optimizer,
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    # Define a custom callback to track the training progress. The below is specifically for identifying
    # why the default output of tensorflow was differing from the callback output. Turns out the default
    # output averages training accuracy and loss over the batches that we've already processed in a given
    # epoch, whereas the callback prints the accuracy and loss for the most recent batch.
    class TrainingCallback(tf.keras.callbacks.Callback):
        def __init__(self):
            super().__init__()
            self.batch_accuracies = []
        def on_train_batch_end(self, batch, logs=None):
            if batch == 0:
                self.batch_accuracies = []
            logs = logs or {}
            self.batch_accuracies.append(logs['accuracy'])
            total_accuracy = self.get_total_accuracy()
            print (f" Batch {batch}: logs={logs}: total_accuracy={total_accuracy}")

        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            print (f" Epoch {epoch}: logs={logs}")
            self.task.update_state(state='PROGRESS', meta={'epoch': epoch + 1, 'logs': logs})

        def get_total_accuracy(self):
            return np.sum(self.batch_accuracies)
    
    # Testing the same as the training callback, just for the testing set.
    class EvaluationCallback(tf.keras.callbacks.Callback):
        def __init__(self):
            super().__init__()
            self.batch_accuracies = []
        def on_test_batch_end(self, batch, logs = None):
            if batch == 0:
                self.batch_accuracies = []
            logs = logs or {}
            self.batch_accuracies.append(logs['accuracy'])
            total_accuracy = self.get_total_accuracy()
            print(f"Test batch {batch}: logs={logs}: total_accuracy={total_accuracy}")
        def get_total_accuracy(self):
            return np.sum(self.batch_accuracies)

    # Train the model
    history = model.fit(
        train_generator,
        epochs=epochs,
        validation_data=val_generator,
        callbacks=[TrainingCallback(task=self)],

    )
    # loss_history = history.history["loss"] #type is list
    # for i in range(len(loss_history)):
    #     print("Epoch %i :"%i, loss_history[i])
    # Evaluate the model on the test set
    test_loss, test_accuracy = model.evaluate(test_generator, callbacks = [EvaluationCallback()])
    # logging.info(f"Test accuracy: {test_accuracy}, test loss: {test_loss}")
    response = {'test_accuracy': test_accuracy, 'test_loss': test_loss}
    return response
