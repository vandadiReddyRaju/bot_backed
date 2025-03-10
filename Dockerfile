# Use Python base image
FROM python:3.9-slim

# Install system dependencies and Docker
RUN apt-get update && \
    apt-get install -y \
    curl \
    && curl -fsSL https://get.docker.com -o get-docker.sh \
    && chmod +x get-docker.sh \
    && ./get-docker.sh \
    && rm get-docker.sh \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create workspace directory with proper permissions
RUN mkdir -p /home/workspace && chmod -R 777 /home/workspace

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV WORKSPACE_ROOT=/home/workspace
ENV DOCKER_WORKSPACE=/home/workspace
ENV PORT=5000
ENV HOST=0.0.0.0

# Expose port 5000
EXPOSE 5000

# Start Docker daemon and run the application
CMD service docker start && dockerd & sleep 5 && python app.py
