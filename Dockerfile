# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copy all code
COPY . .

# Run script when container starts
CMD ["python", "update_labels.py"]
