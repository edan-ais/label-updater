# ==============================
# Dockerfile for label-updater
# ==============================

# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files from repo into container
COPY . /app

# Install required Python packages
RUN pip install --no-cache-dir --upgrade \
    google-api-python-client \
    google-auth \
    google-auth-httplib2 \
    google-auth-oauthlib \
    PyMuPDF \
    python-dotenv

# Run the label updater script
CMD ["python", "update_labels.py"]
