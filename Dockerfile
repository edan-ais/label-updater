# ==============================
# Dockerfile for label-updater (Cloud Run Job)
# ==============================

# Use official Python 3.11 slim base image
FROM python:3.11-slim

# Install system deps (PyMuPDF relies on MuPDF libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmupdf-dev \
        gcc \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first (to leverage Docker caching)
COPY requirements.txt /app/

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . /app

# Default command: run the script once and exit
CMD ["python", "update_labels.py"]
