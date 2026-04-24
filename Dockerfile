"""Production Dockerfile for Project Kernel Runtime."""
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt requirements-prod.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY main.py ./

# Create non-root user for security
RUN useradd -m -u 1000 runtime && chown -R runtime:runtime /app
USER runtime

# Expose port
EXPOSE 8089

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8089/health || exit 1

# Start command
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8089"]
