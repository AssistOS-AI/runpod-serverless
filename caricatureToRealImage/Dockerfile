from python:3.11.1-buster

WORKDIR /

RUN pip install -r requirements.txt

ADD handler.py .

CMD [ "python", "-u", "/handler.py" ]