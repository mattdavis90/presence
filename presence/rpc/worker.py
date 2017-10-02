import pickle
from time import sleep, time

import structlog
import zmq.green as zmq

from .. import config
from . import DISCONNECT, HEARTBEAT, READY, REPLY, REQUEST, STATS, WORKER
from .utils import get_usage

log = structlog.getLogger()


class Worker(object):
    def __init__(self, broker, instance, service_suffix=''):
        self._broker = broker
        self._instance = instance
        self._service = bytes('{}{}'.format(instance.__class__.__name__, service_suffix), 'utf8')

        self._heartbeat_liveness = config['heartbeat_liveness']
        self._heartbeat_interval = config['heartbeat_interval']
        self._reconnect_interval = config['reconnect_interval']
        self._timeout = config['worker_timeout']

        self._liveness = 0
        self._heartbeat_at = 0
        self._expect_reply = False
        self._reply_to = None

        self._context = zmq.Context()
        self._poller = zmq.Poller()
        self._sock = None

    def start(self):
        self._connect_to_broker()

        reply = None
        while True:
            message = self._recv(reply)

            if message is None:
                break

            assert len(message) == 1
            message = message[0]

            reply = None

            (cls_name, attr_name, args, kwargs) = pickle.loads(message)
            log.debug(
                'Call received',
                cls_name=cls_name,
                attr_name=attr_name,
                args=args,
                kwargs=kwargs
            )

            if not cls_name == self._service:
                reply = NameError(
                    'Attempt to call remote function on instance of \'{}\' as \'{}\''.
                    format(self._service, cls_name)
                )

            if not hasattr(self._instance, attr_name):
                reply = AttributeError(
                    'Remote {} instance has no attribute \'{}\''.
                    format(cls_name, attr_name)
                )

            attr = getattr(self._instance, attr_name)

            if callable(attr):
                try:
                    reply = attr(*args, **kwargs)
                except Exception as exc:
                    reply = exc
            else:
                reply = attr

            log.debug('Replying', reply=reply)

            reply = pickle.dumps(reply)

    def _connect_to_broker(self):
        log.info('Connecting to broker', broker=self._broker)

        if self._sock:
            log.info('Old socket expired. Creating new one.')
            self._poller.unregister(self._sock)
            self._sock.close()

        self._sock = self._context.socket(zmq.DEALER)
        self._sock.linger = 0
        self._sock.connect(self._broker)
        self._poller.register(self._sock, zmq.POLLIN)

        self._send_to_broker(READY, self._service)

    def _send_to_broker(self, command, option=None, message=[]):
        if not isinstance(message, list):
            message = [message]

        if option is not None:
            message = [option] + message

        message = [b'', WORKER, command] + message

        log.debug('Sending message to broker', message=message)

        self._sock.send_multipart(message)

    def _recv(self, reply=None):
        assert reply is not None or not self._expect_reply

        if reply is not None:
            if not isinstance(reply, list):
                reply = [reply]

            assert self._reply_to is not None

            reply = [self._reply_to, b''] + reply

            self._send_to_broker(REPLY, message=reply)

        self._expect_reply = True

        while True:
            try:
                items = self._poller.poll(self._timeout)
            except KeyboardInterrupt:
                break

            if items:
                message = self._sock.recv_multipart()

                log.debug('Message received', message=message)

                self._liveness = self._heartbeat_liveness

                assert len(message) >= 3

                empty = message.pop(0)
                assert empty == b''

                header = message.pop(0)
                assert header == WORKER

                command = message.pop(0)
                if command == REQUEST:
                    self._reply_to = message.pop(0)

                    empty = message.pop(0)
                    assert empty == b''

                    return message
                elif command == HEARTBEAT:
                    pass
                elif command == STATS:
                    self._handle_stats(message)
                elif command == DISCONNECT:
                    self._connect_to_broker()
                else:
                    log.error('Invalid message', message=message)
            else:
                self._liveness -= 1

                if self._liveness == 0:
                    log.warn('Disconnected from broker')

                    try:
                        sleep(1e-3 * self._reconnect_interval)
                    except KeyboardInterrupt:
                        break

                    self._connect_to_broker()

            if time() > self._heartbeat_at:
                self._send_to_broker(HEARTBEAT)
                self._heartbeat_at = time() + 1e-3 * self._heartbeat_interval

        log.warn('Interrupted')
        return None

    def _handle_stats(self, message):
        assert len(message) == 1

        client = message.pop(0)

        reply = [client, b'', pickle.dumps(get_usage())]

        self._send_to_broker(REPLY, message=reply)
