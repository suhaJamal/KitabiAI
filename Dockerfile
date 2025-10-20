# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY main.py .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Set environment variables (defaults, can be overridden at runtime)
ENV FLASK_APP=main.py
ENV PYTHONUNBUFFERED=1

# Run the application
# Environment variables will be passed at runtime via docker-compose or docker run -e
CMD ["python", "main.py"]

#COPY .env .env

