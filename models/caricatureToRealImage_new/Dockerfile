FROM python:3.11.1-buster

RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

# Set the working directory to the app root
WORKDIR /

COPY . /

# Set the working directory to the specific model directory
WORKDIR /models/caricatureToRealImage_new

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the application
CMD ["python", "-u", "handler.py"]
