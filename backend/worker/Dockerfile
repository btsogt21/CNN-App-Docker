FROM tensorflow/tensorflow:latest-gpu 

WORKDIR /backend/worker

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# --ignore-installed

# blinker

COPY . .

# ENV PYTHONPATH /backend