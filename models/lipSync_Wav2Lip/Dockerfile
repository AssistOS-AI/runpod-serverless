FROM python:3.11.1-buster

WORKDIR /

COPY . /

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /models
RUN git clone https://github.com/Rudrabha/Wav2Lip.git

WORKDIR /models/Wav2Lip

RUN pip install -r /requirements.txt

RUN pip install opencv-python-headless numpy scipy torch librosa

ENV PATH="/usr/bin/ffmpeg:${PATH}"

WORKDIR /models/lipSync_Wav2Lip

RUN pip install -r requirements.txt

CMD ["python", "-u", "handler.py"]
