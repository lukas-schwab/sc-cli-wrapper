# --- Build Stage (Optional but keeps it clean) ---
FROM python:3.11-slim

# Define version and arch as build arguments
ARG SC_VERSION=latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Detect architecture and install Scalable CLI
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        SC_ARCH="x86_64"; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        SC_ARCH="aarch64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    # If version is 'latest', fetch the tag from GitHub API
    if [ "$SC_VERSION" = "latest" ]; then \
        SC_VERSION=$(curl -s https://api.github.com/repos/ScalableCapital/scalable-cli/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/'); \
    fi && \
    DOWNLOAD_URL="https://github.com/ScalableCapital/scalable-cli/releases/download/${SC_VERSION}/sc-${SC_VERSION}-linux-${SC_ARCH}-gnu.tar.gz" && \
    echo "Downloading Scalable CLI ($SC_VERSION) for $SC_ARCH from: $DOWNLOAD_URL" && \
    curl -L -f -o sc.tar.gz "$DOWNLOAD_URL" && \
    tar -xzf sc.tar.gz --strip-components=1 && \
    mv sc /usr/local/bin/sc && \
    chmod +x /usr/local/bin/sc && \
    rm sc.tar.gz

# Set up workdir
WORKDIR /app

# Create default config to use file-based keyring (necessary for Docker/Headless environments)
RUN mkdir -p /root/.config/scalable-cli && \
    echo '[auth]\nsession_backend = "file"' > /root/.config/scalable-cli/config.toml

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SC_PATH=/usr/local/bin/sc

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
