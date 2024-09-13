FROM python:3.11.1-buster

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake

# Set the working directory to the app root
WORKDIR /app

COPY . /app

# Ensure model is copied
COPY inswapper_128.onnx /app/inswapper_128.onnx

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "-u", "handler.py"]
