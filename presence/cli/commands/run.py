import pickle

import click
import structlog
import zmq.green as zmq

from click_didyoumean import DYMGroup
from zmq.green.eventloop.ioloop import IOLoop
from zmq.green.eventloop.zmqstream import ZMQStream

from presence.cli import cli


log = structlog.getLogger()


@cli.group(cls=DYMGroup)
def run():
    pass


class Registry(object):
    def register(self):
        return True


def make_remote(cls):
    class Remote(object):
        def __init__(self, *args, **kwargs):
            self._wrapped = cls(*args, **kwargs)

            context = zmq.Context()
            self._sock = context.socket(zmq.REQ)
            self._sock.connect('tcp://registry:5000')

        def __getattr__(self, name):
            log.info('Calling {} on {}'.format(name, self))
            self._sock.send(pickle.dumps((self._wrapped.__class__.__name__, name)))

    return Remote


@run.command()
def registry():
    """Run the registry"""
    log.info('Running Registry...')

    context = zmq.Context()
    sock = context.socket(zmq.REP)
    ioloop = IOLoop()

    sock.bind('tcp://*:5000')
    stream = ZMQStream(sock, ioloop)

    def cb(messages):
        for message in messages:
            log.info('Message receieved', msg=pickle.loads(message))

    stream.on_recv(cb)
    ioloop.start()


@run.command()
def test():
    reg = make_remote(Registry)()
    print(reg.register())
