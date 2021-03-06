FROM python:alpine

RUN apk --no-cache add --virtual build-deps python-dev build-base gcc linux-headers

RUN pip install pyzmq gevent psutil

RUN mkdir /code

WORKDIR /code

ADD . /code

VOLUME /config

RUN pip install -e .
