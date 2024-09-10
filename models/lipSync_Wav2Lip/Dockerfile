FROM python:3.11.1-buster

WORKDIR /

COPY . /

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/Rudrabha/Wav2Lip.git /models/Wav2Lip

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

ENV PATH="/usr/bin/ffmpeg:${PATH}"

CMD ["python", "-u", "handler.py"]
