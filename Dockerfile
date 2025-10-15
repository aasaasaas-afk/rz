# Use official Python slim image for smaller footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port (Render dynamically assigns port, default to 2020 for local)
EXPOSE 2020

# Set environment variable for Flask
ENV FLASK_APP=app.py

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
