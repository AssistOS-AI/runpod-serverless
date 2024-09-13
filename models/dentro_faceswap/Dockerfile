FROM python:3.11.1-buster

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
    wget  # Adăugăm wget pentru descărcarea modelului

# Copiezi toate fișierele proiectului în directorul curent
COPY . .

# Download the model
RUN wget -O inswapper_128.onnx https://huggingface.co/spaces/Dentro/face-swap/resolve/main/inswapper_128.onnx

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "-u", "handler.py"]
