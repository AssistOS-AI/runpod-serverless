# Folosim imaginea python 3.11.1-buster ca bază
FROM python:3.11.1-buster

# Instalăm dependențele de sistem necesare
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
    wget  # Pentru descărcarea modelului

# Setăm directorul de lucru la rădăcina containerului
WORKDIR /

# Copiem toate fișierele proiectului în directorul curent
COPY . /

# Set the working directory to the specific model directory
WORKDIR /models/dentro_faceswap

# Descărcăm modelul ONNX în directorul curent
RUN wget -O /inswapper_128.onnx https://huggingface.co/spaces/Dentro/face-swap/resolve/main/inswapper_128.onnx

# Instalăm dependențele Python specificate în requirements.txt
RUN pip install  -r requirements.txt

# Comandă pentru a rula aplicația
CMD ["python", "-u", "handler.py"]
