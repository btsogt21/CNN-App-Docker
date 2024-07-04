FROM tensorflow/tensorflow:latest-gpu

# figure out if the above image is necessary given we've delegated training to the 
# celery worker.

WORKDIR /backend

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# --ignore-installed

# blinker

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]