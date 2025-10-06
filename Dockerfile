FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    gcc \
    ca-certificates \
    libssl-dev \
    curl \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "web_app.py"]
