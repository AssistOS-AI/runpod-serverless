FROM python:3.11.1-buster

# Install git and other dependencies
RUN apt-get update && apt-get install -y git
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

# Set the working directory to root
WORKDIR /

# Copy all contents of the current directory to the container
COPY . /

# Clone the Wav2Lip repo into the current directory
RUN git clone https://github.com/Rudrabha/Wav2Lip.git

# Set the working directory to the Wav2Lip directory
WORKDIR /Wav2Lip

# Install Python dependencies specific to Wav2Lip
RUN pip install librosa==0.7.0 numpy==1.17.1 opencv-contrib-python>=4.2.0.34 opencv-python==4.1.0.25 torchvision==0.3.0 tqdm==4.45.0 numba==0.48 --no-cache-dir

# Install additional dependencies from requirements.txt
WORKDIR /models/lipSync_Wav2Lip
RUN pip install -r requirements.txt

# Ensure correct versions of torch and torchvision
RUN pip install torch==2.1.0 torchvision==0.16.0

# Clean up to reduce image size
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
