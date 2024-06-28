# Description: This file contains the code for the Flask API that will be used to train the model. 
# The API will accept a JSON object containing the model configuration and hyperparameters, train 
# the model on the CIFAR-10 dataset, and return the test accuracy and loss of the model.
# 
# Flask Imports
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_socketio import SocketIO, emit

# FastAPI Imports
from fastapi import FastAPI
from celery.result import AsyncResult
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from worker import train_model

#uvicorn imports
import uvicorn

# Create a FastAPI instance
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

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

@app.get("/training-status/{task_id}")
async def training_status(task_id: str):
    task = AsyncResult(task_id)
    if task.state == 'SUCCESS':
        return JSONResponse({
            "test_accuracy": task.get()['test_accuracy'],
            "test_loss": task.get()['test_loss']
        })

if __name__ == '__main__':
    uvicorn.run("app:socket_app", host = "0.0.0.0", port = 5000, reload = True)



# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('script.log'),
#         logging.StreamHandler()
#     ]
# )