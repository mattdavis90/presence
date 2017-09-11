FROM python:alpine

RUN apk --no-cache add --virtual build-deps python-dev build-base \
&& pip install pyzmq gevent

RUN mkdir /code

WORKDIR /code

ADD . /code

RUN pip install -e .
