# ==============================
# Dockerfile for label-updater (Cloud Run Job with OAuth)
# ==============================

# Base image
FROM python:3.11-slim

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmupdf-dev \
        gcc \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt /app/

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Copy OAuth credentials (make sure credentials.json is in your repo)
COPY credentials.json /app/credentials.json

# Create token.pickle for OAuth caching and make it writable
RUN touch /app/token.pickle && chmod 666 /app/token.pickle

# Set environment variable for OAuth credentials
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/credentials.json"

# Command to run the job
CMD ["python", "update_labels.py"]
