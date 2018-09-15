FROM python:3.7-stretch
RUN apt-get update && apt-get install postgresql netcat -y

COPY requirements.txt /comment_service/requirements.txt

RUN pip install -r /comment_service/requirements.txt

COPY . /comment_service

WORKDIR /comment_service

RUN find . -name "*.pyc" -exec rm -f {} \;
