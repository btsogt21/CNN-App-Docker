FROM tensorflow/tensorflow:latest-gpu

WORKDIR /backend

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# --ignore-installed

# blinker

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

CMD ["python", "app.py"]