FROM tensorflow/tensorflow:latest-gpu

RUN useradd -ms /bin/bash nonrootuser

RUN apt-get update && apt-get install -y tini

WORKDIR /backend

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# --ignore-installed

# blinker

COPY . .

COPY wait-for-it.sh /wait-for-it.sh

RUN chmod +x /wait-for-it.sh

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Change ownership of working directory
RUN chown -R nonrootuser:nonrootuser /backend

USER nonrootuser

# ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 5000

CMD ["python", "app.py"]