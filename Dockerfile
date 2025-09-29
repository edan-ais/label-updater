# Base image
FROM python:3.11-slim

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmupdf-dev \
        gcc \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first
COPY requirements.txt /app/

# Install deps
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Copy OAuth credentials (make sure credentials.json is in your repo or mounted as secret)
COPY credentials.json /app/credentials.json

# Create token.pickle for OAuth caching
RUN touch /app/token.pickle && chmod 666 /app/token.pickle

# Env vars
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/credentials.json"

# Command to run Flask app
CMD ["python", "web_app.py"]
