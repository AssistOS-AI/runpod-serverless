FROM python:3.11.1-buster

# Set the working directory to the app root
WORKDIR /

COPY . /

# Set the working directory to the specific model directory
WORKDIR /models/fluxImageGeneration

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the application
CMD ["python", "-u", "handler.py"]