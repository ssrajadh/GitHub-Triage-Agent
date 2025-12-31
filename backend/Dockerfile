# Backend Dockerfile for GitHub Triage Agent
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (includes chroma_db/ since it's not in .dockerignore)
# Note: Make sure chroma_db directory exists and is indexed before building
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Expose port (Cloud Run will override PORT env var)
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application
# Use PORT env var for Cloud Run compatibility (defaults to 8000 for local)
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
