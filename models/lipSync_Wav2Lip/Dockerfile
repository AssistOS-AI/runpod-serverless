FROM python:3.11.1-buster

RUN apt-get update 

WORKDIR /

COPY . /

WORKDIR /models/lipSync_Wav2Lip

RUN pip install -r requirements.txt

CMD ["python", "-u", "handler.py"]
