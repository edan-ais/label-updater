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

# Copy the rest of the app
COPY . /app

# Copy OAuth credentials (make sure you have these in the project folder)
COPY credentials.json /app/credentials.json
# token.pickle will be created on first run if it doesn't exist

# Make token.pickle writable
RUN touch /app/token.pickle && chmod 666 /app/token.pickle

# Command to run the job
CMD ["python", "update_labels.py"]
