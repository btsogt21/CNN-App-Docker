# Build stage base image, pull and name as 'builder' for later reference
FROM debian:12-slim as builder

# Installing system dependencies, specifically by updating package list and installing gcc (which is)
# needed for compiling some python packages), then cleaning up the package list and removing the
# cache to reduce the image size.
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests --yes gcc pipx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pipx ensurepath

# Update PATH
ENV PATH="/root/.local/bin:${PATH}"

# Install Poetry
RUN pipx install poetry

# Install poetry plugin for creating a virtual environment from a lock file
RUN pipx inject poetry poetry-plugin-bundle

# Set up working directory
WORKDIR /backend

# Copy only the files needed for installation
COPY pyproject.toml poetry.lock README.md ./

# Install dependencies
RUN poetry bundle venv --only=main /backend/venv

# Runtime stage base image.
FROM tensorflow/tensorflow:latest-gpu

# Set up working directory
WORKDIR /backend

# Installing system dependencies, specifically by updating package list and installing gcc (which is)
# needed for compiling some python packages), then cleaning up the package list and removing the
# cache to reduce the image size.
RUN apt-get update && apt-get install -y --no-install-recommends curl tini && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages and application from builder stage
COPY --from=builder /backend /backend

# Making tensorflow accessible in venv
# Add TensorFlow to virtual environment
RUN echo "/usr/local/lib/python3.11/dist-packages" > /backend/venv/lib/python3.11/site-packages/tensorflow.pth

# Restrict Python path to only include the virtual environment and TensorFlow
RUN echo "import sys; sys.path = [p for p in sys.path if '/backend/venv' in p or '/usr/local/lib/python3.11/dist-packages' in p]" > /backend/venv/lib/python3.11/site-packages/sitecustomize.py

# setting environment variable so that python output is sent straight to terminal without buffering
# first
ENV PYTHONNUNBUFFERED=1

COPY entrypoint.sh /entrypoint.sh

COPY . .

RUN chmod +x /entrypoint.sh

# Create non root user.
RUN useradd -ms /bin/bash nonrootuser

# Change ownership of working directory
RUN chown -R nonrootuser:nonrootuser /backend

USER nonrootuser

ENTRYPOINT ["/usr/bin/tini", "--"]

EXPOSE 5000

CMD ["./venv/bin/python", "app.py"]