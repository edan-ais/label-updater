# ==============================
# Dockerfile for label-updater
# ==============================

# Use official Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files from repo into container
COPY . /app

# Upgrade pip and install required Python packages with fixed versions
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade \
       google-api-python-client==2.183.0 \
       google-auth==2.40.3 \
       google-auth-httplib2==0.2.0 \
       google-auth-oauthlib==1.2.2 \
       PyMuPDF==1.26.4 \
       python-dotenv==1.1.1

# Expose default Cloud Run port
ENV PORT=8080

# Run the label updater script by default (Cloud Run Job)
CMD ["python", "update_labels.py"]
