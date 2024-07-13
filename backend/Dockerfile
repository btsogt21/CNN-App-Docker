FROM tensorflow/tensorflow:latest-gpu

RUN useradd -ms /bin/bash nonrootuser

WORKDIR /backend

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# --ignore-installed

# blinker

COPY . .

# Change ownership of working directory

RUN chown -R nonrootuser:nonrootuser /backend

USER nonrootuser

EXPOSE 5000

CMD ["python", "app.py"]