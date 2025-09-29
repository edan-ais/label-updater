# Base image
FROM python:3.11-slim

# Install system dependencies for PyMuPDF and SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmupdf-dev \
        gcc \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Env var: credentials.json will be provided via Render Secret Files
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/credentials.json"

# Command to run Flask app
CMD ["python", "web_app.py"]
