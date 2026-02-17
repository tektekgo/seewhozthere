# SeeWhozThere Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Build React frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ ./

# Build the React app
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY models/ ./models/
COPY run_service.py ./
COPY config.ini.example ./config.ini

# Copy built React frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./app/static/dashboard

# Create data directories
RUN mkdir -p data/snapshots data/thumbnails data/encodings

# Expose port
EXPOSE 7222

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python3 -c "import requests; requests.get('http://localhost:7222/api/status')"

# Run the application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7222"]
