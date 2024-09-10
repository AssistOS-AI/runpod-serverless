# Use an official Python runtime as a base image
FROM python:3.11.1-buster

WORKDIR /

# Copy the entire project to the container
COPY . /

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /models/lipSync_Wav2Lip

RUN git clone https://github.com/Rudrabha/Wav2Lip.git

RUN pip install -r Wav2Lip/requirements.txt

RUN pip install -r requirements.txt

ENV PATH="/usr/bin/ffmpeg:${PATH}"

# Run the application
CMD ["python", "-u", "handler.py"]
