# Use Python base image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create workspace directory
RUN mkdir -p /home/workspace

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV WORKSPACE_ROOT=/home/workspace
ENV DOCKER_WORKSPACE=/home/workspace
ENV PORT=5000
ENV HOST=0.0.0.0

# Create and set permissions for workspace
RUN chmod -R 777 /home/workspace

# Expose port 5000
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
