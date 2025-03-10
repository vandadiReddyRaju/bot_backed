# Use Python base image
FROM python:3.9-slim

# Install system dependencies including Docker
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce docker-ce-cli containerd.io \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create workspace directory
RUN mkdir -p /home/workspace && chmod -R 777 /home/workspace

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

# Expose port 5000
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
