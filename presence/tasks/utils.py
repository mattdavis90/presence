import pickle

import structlog
import zmq.green as zmq
from zmq.green.eventloop.ioloop import IOLoop
from zmq.green.eventloop.zmqstream import ZMQStream


log = structlog.getLogger()


def make_remote(cls, remote_host):
    class Remote(object):
        def __init__(self):
            self._wrapped = cls
            self._wrapped_name = self._wrapped.__name__

            context = zmq.Context()
            self._sock = context.socket(zmq.REQ)

            log.info('{} Connecting to {}'.format(self._wrapped_name, remote_host))
            self._sock.connect(remote_host)

        def __getattr__(self, name):
            if not hasattr(self._wrapped, name):
                raise AttributeError('Remote {} instance has no attribut \'{}\''.format(self._wrapped_name, name))

            def remote_call(*args, **kwargs):
                log.info('Calling {} on {} with {} {}'.format(name, self._wrapped_name, args, kwargs))

                self._sock.send(pickle.dumps((self._wrapped_name, name, args, kwargs)))

                retVal = pickle.loads(self._sock.recv())

                if isinstance(retVal, Exception):
                    raise retVal
                else:
                    return retVal

            if callable(getattr(self._wrapped, name)):
                return remote_call
            else:
                return remote_call()
    return Remote()


def remote_runner(instance, listen):
    instance_name = instance.__class__.__name__

    context = zmq.Context()
    sock = context.socket(zmq.REP)
    ioloop = IOLoop()

    sock.bind(listen)
    stream = ZMQStream(sock, ioloop)

    def callback(messages):
        for message in messages:
            retVal = None

            (wrapped_name, name, args, kwargs) = pickle.loads(message)

            log.info('Message received', wrapped_name=wrapped_name, name=name, args=args, kwargs=kwargs)

            if not instance_name == wrapped_name:
                retVal = NameError('Attempt to call remote function on instance of \'{}\' as \'{}\''.format(instance_name, wrapped_name))
            elif not hasattr(instance, name):
                retVal = AttributeError('Remote {} instance has no attribut \'{}\''.format(instance_name, name))
            else:
                prop = getattr(instance, name)

                if callable(prop):
                    try:
                        retVal = prop(*args, **kwargs)
                    except Exception as exc:
                        retVal = exc
                else:
                    retVal = prop

            sock.send(pickle.dumps(retVal))

    stream.on_recv(callback)
    ioloop.start()
