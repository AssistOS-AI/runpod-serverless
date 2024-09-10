FROM python:3.11.1-buster


WORKDIR /

COPY . /

WORKDIR /models/lipSync_Wav2Lip

RUN pip install -r requirements.txt

CMD ["python", "-u", "handler.py"]
