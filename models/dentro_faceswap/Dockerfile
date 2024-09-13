FROM python:3.11.1-buster

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
    wget  # Adaugă wget pentru a descărca modelul

# Set the working directory to the app root
WORKDIR /app

COPY . /app

# Download the model
RUN wget -O /app/inswapper_128.onnx https://huggingface.co/spaces/Dentro/face-swap/resolve/main/inswapper_128.onnx

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "-u", "handler.py"]
