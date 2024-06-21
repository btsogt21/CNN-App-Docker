# Description: This file contains the code for the Flask API that will be used to train the model. 
# The API will accept a JSON object containing the model configuration and hyperparameters, train 
# the model on the CIFAR-10 dataset, and return the test accuracy and loss of the model.
# 
# Flask Imports
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit


#preprocessing imports
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import numpy as np

#model building and training imports
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator


# Create a Flask app

app = Flask(__name__)

# Create a SocketIO instance
# This line sets the SECRET_KEY configuration variable for the flask application 'app'.
# This is a critical configuration used by Flask to securely sign session cookies and other security-related
# needs. Essential for keeping client side sessions secure. Here, it's being set to a static 'secret!' which
# is not recommended for production. Should be a hard to guess string to ensure app security, and
# should be read in from your environment variable to keep it out of your source code.
app.config['SECRET_KEY'] = 'temp_secret!'

# This line initalizes a new SocketIO instance with the Flask application app as its argument. 
# SocketIO is a library that facilitates real-time communication between clients and the server 
# over WebSockets. The cors_allowed_origins="*" parameter configures Cross-Origin Resource Sharing 
# (CORS) settings for the SocketIO instance, allowing connections from any domain ("*"). 
# This is useful for development but should be more restrictive in production environments to 
# prevent unwanted access from other domains.
socketio = SocketIO(app, cors_allowed_origins="*")

# Enable CORS
# This line configures Cross-Origin Resource Sharing (CORS) for the Flask application. 
# It specifies that all routes (denoted by "/*") are allowed to accept HTTP requests originating 
# from "http://localhost:5173". This is essential for enabling web applications hosted on this 
# origin to make requests to the Flask backend without violating the same-origin policy.
CORS(app, resources = {r"/*": {"origins": "http://localhost:5173"}})


# Function decorated with @socketio.on('connect'). Runs when client connects with server over 
# WebSocket. Primary purpose is to handle any initial setup or acknowledgements required when a new
# client connects. In this case, it simply prints a message. Could later be used to initalize client
# specific resources or data structures.
@socketio.on('connect')
def handle_connect():
    print('Client connected')

# Same thing as the above but for when a client disconnects. Should probably be used later to handle
# termination or saving of ongoing training processes or data.
@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/train', methods=['POST'])
def train_model():
    data = request.get_json()
    layers = data['layers']
    units = data['units']
    epochs = data['epochs']
    batch_size = data['batchSize']
    optimizer = data['optimizer']

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

    class TrainingCallback(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            socketio.emit('training_progress', {'epoch': epoch, 'logs': logs})

    # Train the model
    history = model.fit(
        train_generator,
        epochs=epochs,
        validation_data=val_generator,
        callbacks=[TrainingCallback()]
    )
    # Evaluate the model on the test set
    test_loss, test_accuracy = model.evaluate(test_generator)
    response = {'test_accuracy': test_accuracy, 'test_loss': test_loss}
    return jsonify(response)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)