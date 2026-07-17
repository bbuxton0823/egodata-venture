FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download MediaPipe model
RUN mkdir -p models && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -sL -o models/hand_landmarker.task \
    https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task && \
    apt-get remove -y curl && rm -rf /var/lib/apt/lists/*

COPY *.py .
COPY models/ models/

ENTRYPOINT ["python", "pipeline_poller.py"]
