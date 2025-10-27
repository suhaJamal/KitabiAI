# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies for PDF processing and downloading FastText model
RUN apt-get update && apt-get install -y \
    gcc \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download FastText language identification model
# This is a ~900KB compressed model for 176 languages
RUN echo "Downloading FastText model..." && \
    wget -q --timeout=60 --tries=3 \
    https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz \
    -O /app/lid.176.ftz || \
    (echo "Primary download failed, trying with curl..." && \
    curl -L -o /app/lid.176.ftz \
    https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz) && \
    echo "FastText model downloaded successfully" && \
    ls -lh /app/lid.176.ftz

# Copy application code (this includes main.py inside app/)
COPY app/ ./app/

# Copy validation scripts (for language detection testing)
COPY validate_language_detection.py .
COPY validate_language_detection_fasttext.py .
COPY debug_pdf_extraction.py .
COPY download_fasttext_model.py .

# Create necessary directories
RUN mkdir -p logs && \
    mkdir -p /mnt/user-data/uploads && \
    mkdir -p /mnt/user-data/outputs && \
    mkdir -p outputs

# Expose port
EXPOSE 8000

# Set environment variables (defaults, can be overridden at runtime)
ENV PYTHONUNBUFFERED=1

# Run the application with uvicorn (FastAPI's ASGI server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
