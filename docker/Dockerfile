# Use multi-stage build for smaller image size
FROM python:3.12-slim as builder

WORKDIR /app

# Install system dependencies required for building python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
# ffmpeg is required for Discord Voice (PyCord)
# espeak-ng is often required for Piper/TTS backends
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project files
COPY . .

# Set python path
ENV PYTHONPATH=/app

# Default command (overridden by docker-compose)
CMD ["python", "bot/main.py"]
