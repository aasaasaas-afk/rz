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

# Expose default port 10000
EXPOSE 10000

# Use entrypoint to handle dynamic PORT, default to 10000, with optimized Gunicorn settings
ENTRYPOINT ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 60 app:app"]
