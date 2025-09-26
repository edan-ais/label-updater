# ==============================
# Dockerfile for label-updater (Cloud Run Compatible)
# ==============================

# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt /app/requirements.txt

# Install required Python packages
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the rest of the application code
COPY . /app

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Start the Flask web server
CMD ["python", "main.py"]
