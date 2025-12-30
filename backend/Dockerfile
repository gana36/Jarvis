# Use Python 3.10 slim image for smaller footprint
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (needed for grpcio, google-cloud packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better layer caching
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app ./app

# Create uploads directory
RUN mkdir -p uploads

# Cloud Run uses PORT env variable, default to 8080
ENV PORT=8080
EXPOSE 8080

# Run the application - use PORT env variable for Cloud Run compatibility
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
