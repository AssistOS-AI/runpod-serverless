FROM python:3.11.1-buster

# Install git and other dependencies
RUN apt-get update && apt-get install -y git
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

# Set the working directory to root
WORKDIR /

# Copy all contents of the current directory to the container
COPY . /

# Set the working directory to the specific model directory
WORKDIR /models/lipSync_Wav2Lip

# Install Python dependencies
RUN pip install -r requirements.txt

# Clone the Wav2Lip repo into the current directory
RUN git clone https://github.com/Rudrabha/Wav2Lip.git && \
    cd Wav2Lip && \
    pip install torch torchvision torchaudio numpy opencv-python moviepy librosa --no-cache-dir

# Define the command to run the application
CMD ["python", "-u", "handler.py"]
