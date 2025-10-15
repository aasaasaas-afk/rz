# Use official Python slim image for smaller footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose default port
EXPOSE 5000

# Use entrypoint script to handle PORT
ENTRYPOINT ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} app:app"]
