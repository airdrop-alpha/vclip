FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/tmp /app/data/clips

# Environment
ENV VCLIP_DATA_DIR=/app/data
ENV VCLIP_DB_PATH=/app/data/vclip.db
ENV VCLIP_TEMP_DIR=/app/data/tmp
ENV VCLIP_CLIPS_DIR=/app/data/clips
ENV VCLIP_WHISPER_MODEL=large-v3
ENV VCLIP_WHISPER_DEVICE=auto
ENV VCLIP_WHISPER_COMPUTE=float16

EXPOSE 8000

CMD ["python", "-m", "app.main"]
