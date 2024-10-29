FROM python:3.10-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    espeak-ng \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to the app root
WORKDIR /

COPY . /

# Set the working directory to the specific model directory
WORKDIR /models/cuquiXTTSv2

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "-u", "handler.py"]