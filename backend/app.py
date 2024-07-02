# META

# Two active print statements currently, both for exceptions.

# Description: This file contains the code for the Flask API that will be used to train the model. 
# The API will accept a JSON object containing the model configuration and hyperparameters, train 
# the model on the CIFAR-10 dataset, and return the test accuracy and loss of the model.
# 
# Flask Imports
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_socketio import SocketIO, emit

# FastAPI Imports
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Celery imports
from worker import train_model
from celery.result import AsyncResult

# uvicorn imports
import uvicorn

# Other importsas
import redis.asyncio as aioredis
import asyncio
import json

# Create a FastAPI instance
app = FastAPI()

# .add_middleware() is a method that allows us to add middleware to a FastAPI application.
# Middleware is a function that runs before and after every request.
# Here, we are adding the CORSMiddleware to allow requests from a specific origin, and then configuring
# options such as allowed methods, headers, and whether or not to allow credentials (cookies, 
# authorization headers, TLS client certificates, etc.) to go through.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["post"],
    allow_headers=["*"]
)

# Define a global variable to store the active WebSocket connection.
redis_client = aioredis.from_url("redis://redis:6379")

# Route for the WebSocket connection. "@app.websocket(/ws)" is a decorator that defines a WebSocket
# endpoint at the specified path. The decorated function has a websocket parameter that takes as
# input the WebSocket connection. The function accepts the WebSocket connection and then enters a
# loop to receive messages from the client.
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # accept() is used to accept the WebSocket connection by
    # sending a response to the client (that is, the websocket client on the frontend)
    # that the connection has been established. We use await
    # here so that execution is paused until the connection is accepted. By 'execution is paused'
    # we mean that the function will not proceed to the next line until the connection is accepted.
    await websocket.accept()
    global active_connection
    # assigning the current websocket connection to the global variable active_connection.
    # Alllows the rest of hte code to access the active websocket connection.
    active_connection = websocket
    try:
        while True:
            # receive_text() is an asynchronous function that waits for a message to be received
            await websocket.receive_text()
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    # finally block is executed after the try block has completed and any exceptions have been handled.
    # We're basically just cleaning up here by closing the connection.
    finally:
        active_connection = None

# broadcast() is an asynchronous function that sends a message to the active WebSocket connection.
# It uses the .send_text() method of the WebSocket connection to send the message.
async def broadcast(message):
    await active_connection.send_text(message)

# redis_listener() is an asynchronous function that listens for messages on a Redis channel. It uses
# asynchronous Redis client to subscribe to the 'model_updates' channel and then enters a loop to
# receive messages. When a message is received, it is broadcast to the active WebSocket connection.
async def redis_listener():
    # pubsub() is a method that creates a new PubSub instance. PubSub is a messaging pattern where
    # publishers send messages to a channel, and subscribers listen for messages on that channel.
    # The publisher in this case is the redis client in the worker.py containing the training task, 
    # and the subscriber is the pubsub object created here.
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('model_updates')
    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                message_data = json.loads(message['data'])
                await broadcast(json.dumps(message_data))
        except Exception as e:
            print(f"Redis error: {e}")
        await asyncio.sleep(0.01)

# Decorator that runs the startup_event() function when the "startup" event is triggered. 
# The startup event is triggered when the application starts up. This function creates a task
# to run the redis_listener() function asynchronously.
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())



# Decorator that runs the train_model_request() function when a POST request is made to the "/train" 
# endpoint. The function accepts a JSON payload containing the model configuration and hyperparameters,
# and then calls the train_model.delay() function from the worker.py file.
@app.post("/train")
async def train_model_request(payload: dict):
    task = train_model.delay(
        layers = payload['layers'],
        units = payload['units'],
        epochs = payload['epochs'],
        batch_size = payload['batchSize'],
        optimizer = payload['optimizer']
    )
    return {"task_id": task.id}

if __name__ == '__main__':
    uvicorn.run("app:app", host = "0.0.0.0", port = 5000, reload = True)
