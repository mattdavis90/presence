FROM python:alpine

RUN apk --no-cache add --virtual build-deps python-dev build-base \
&& pip install pyzmq gevent

RUN mkdir /code

WORKDIR /code

ADD . /code

VOLUME /config

RUN pip install -e .
