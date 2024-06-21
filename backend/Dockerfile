FROM tensorflow/tensorflow:latest-gpu

WORKDIR /backend

COPY requirements.txt requirements.txt

RUN pip install --ignore-installed --no-cache-dir blinker -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

CMD ["python", "app.py"]