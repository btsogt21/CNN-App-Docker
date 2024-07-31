# FastAPI Imports
from fastapi import FastAPI, WebSocket, HTTPException, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Celery import
from celery.result import AsyncResult

# Uvicorn imports
import uvicorn

# Redis import
import redis.asyncio as aioredis

# Other imports
import asyncio
import json
import signal
import sys
from contextlib import asynccontextmanager
import os
import logging

# Internal imports
from models import TrainModelRequest, CancelTaskRequest
from worker import train_model
from loggingConfig import configure_logging

# Environment Variables
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

# Logging imports and config

# Call this function to configure logging. This function removes any existing handlers from the root
# logger, sets the log level to INFO, creates a StreamHandler that writes log messages to stdout, sets
# 
configure_logging()

# Then use logging as usual
logger = logging.getLogger(__name__)
logger.info("Starting logging")


# Define a global variable redis_client that will be used to connect to the Redis server.
redis_client = None

# Define an asynchronous context manager lifespan() that connects to the Redis server when the FastAPI
# application starts up and closes the connection when the application shuts down. The context manager
# is used to manage the lifecycle of the Redis connection, ensuring that the connection is established
# before the application starts processing requests and closed when the application is shut down.
# Note that the redis client is a global variable that is used to connect to the Redis server. It is
# not the redis server itself. The shutdown of the redis server is handled internally by docker. The
# redis server is also stateless, thus not requiring the same shutdown procedures as the redis client.
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    retries = 0
    while retries > 5:
        try:
            global redis_client
            redis_client = aioredis.from_url(REDIS_URL)
            asyncio.create_task(redis_listener())
            logger.info("Application starting...")
            break
        except Exception as e:
            retries += 1
            logger.warning(f"{retries} attempt to connect to Redis failed, retrying : {e}", exc_info=True)
    yield
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed.")

# Create a FastAPI instance
app = FastAPI(lifespan=lifespan)

# .add_middleware() is a method that allows us to add middleware to a FastAPI application.
# Middleware is a function that runs before and after every request.
# Here, we are adding the CORSMiddleware to allow requests from a specific origin, and then configuring
# options such as allowed methods, headers, and whether or not to allow credentials (cookies, 
# authorization headers, TLS client certificates, etc.) to go through.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"]
)

# Defining a global exception handler to catch all unhandled exceptions in the application.
# It takes two arguments, request and exc, where request is the incoming request that caused the
# exception, and exc is the exception that was raised. The function logs the exception and returns
# a JSONResponse with a status code of 500 (Internal Server Error) and a message indicating that an
# unexpected error occurred. The headers parameter is used to allow requests from a specific origin.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f'Unhandled exception triggered global exception handler: {exc}', exc_info = True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred. Please try again later. Err: {exc}"},
        headers = {
        "Access-Control-Allow-Origin": "http://localhost:5173",
        }
    )



# Exception handler to handle validation errors. When a validation error occurs, this function
# returns a JSONResponse with status code 422 (Unprocessable Entity) and the details of the validation
# errors. "request: Request" is the incoming request that caused the validation error, and "exc: RequestValidationError"
# is the exception that was raised.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f'Validation error triggered validation exception handler: {exc}', exc_info = True)
    errors = []
    for error in exc.errors():
        errors.append({"origin": "Input Validation Error after POST request to /train or /cancel",
                       "loc": error["loc"],
                       "msg": error["msg"],
                       "type": error["type"]})
    return JSONResponse(status_code=422, content={"detail": errors})

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
            await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled.")
            break
        except Exception as e:
            logger.error(f"Redis error: {e}", exc_info=True)
            # raise
            break

# broadcast() is an asynchronous function that sends a message to the active WebSocket connection.
# It uses the .send_text() method of the WebSocket connection to send the message.
async def broadcast(message):
    await active_connection.send_text(message)

# Route for the WebSocket connection. "@app.websocket(/ws)" is a decorator that defines a WebSocket
# endpoint at the specified path. The decorated function has a websocket parameter that takes as
# input the WebSocket connection. The function accepts the WebSocket connection and then enters a
# loop to receive messages from the client.

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # accept() is used to accept the WebSocket connection by
    # sending a response to the client (that is, the websocket client on the frontend)
    # that the connection has been established. We use await
    # here so that execution is paused until the connection is accepted. By 'execution is paused'
    # we mean that the function will not proceed to the next line until the connection is accepted.
    logger.info("WebSocket connection establishing")
    await websocket.accept()
    global active_connection
    # assigning the current websocket connection to the global variable active_connection.
    # Alllows the rest of hte code to access the active websocket connection.
    active_connection = websocket
    try:
        while True:
            # receive_text() is an asynchronous function that waits for a message to be received
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    
    # finally block is executed after the try block has completed and any exceptions have been handled.
    # We're basically just cleaning up here by closing the connection.
    finally:
        logger.info("Closing connection")
        active_connection = None


# Decorator that runs the train_model_request() function when a POST request is made to the "/train" 
# endpoint. The function accepts a JSON payload containing the model configuration and hyperparameters,
# and then calls the train_model.delay() function from the worker.py file. The pydantic model
# TrainModelRequest is used to validate the input payload, returning a 422 error if the payload is invalid.
# If the payload is valid, a Celery task is created to train the model, and the task ID is returned 
# in the response. If there is an error, an HTTPException is raised with a status code of 500 
# (Internal Server Error) and the error message.
@app.post("/train")
async def train_model_request(payload: TrainModelRequest):
    try:
        task = train_model.delay(
            layers = payload.layers,
            units = payload.units,
            epochs = payload.epochs,
            batch_size = payload.batchSize,
            optimizer = payload.optimizer
        )
        return {"task_id": task.id}
    except Exception as e:
        logging.error(f"Error training model: {e}")
        raise HTTPException(status_code=500, detail=f"Error running train_model.delay() and assigning it to a celery task. Exception: {e}")

@app.post("/cancel")
async def cancel_task(payload : CancelTaskRequest):
    try:
        logger.info(f'here in cancel task {payload.task_id}')
        task = AsyncResult(payload.task_id)
        task.revoke(terminate=True)
        return {"status": "Task cancelled"}
    except Exception as e:
        logging.error(f"Error cancelling task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cancelling task. Exception: {e}")

@app.get("/test-error")
async def test_error():
    raise Exception("Deliberate Test Exception")




# defining a function handle_exit() that will be called when a SIGINT or SIGTERM signal is received.
# takes a variable number of arguments (*args) and prints a message to the console before exiting the
# application with a status code of 0.
def handle_exit(*args):
    logger.info('Received exit signal, exiting...')
    sys.exit(0)

# signal.signal(signal.SIGINT, handle_exit)
# signal.signal(signal.SIGTERM, handle_exit)

if __name__ == '__main__':
    # signal.signal() is used to set the handler for the SIGINT (Ctrl+C) and SIGTERM (termination) signals.
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    uvicorn.run("app:app", host = "0.0.0.0", port = (os.getenv("PORT", 5000)), reload = False)