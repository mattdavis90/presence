import pickle

import structlog
import zmq.green as zmq

from . import CLIENT, TimeoutException

log = structlog.getLogger()


class Client(object):
    def __init__(self, broker, cls):
        self._broker = broker
        self._wrapped_cls = cls
        self._service = bytes(cls.__name__, 'utf8')

        self._context = zmq.Context()
        self._poller = zmq.Poller()
        self._sock = None

        self._retries = 3
        self._timeout = 2500

        self._connect_to_broker()

    def _connect_to_broker(self):
        log.info('Connecting to broker', broker=self._broker)

        if self._sock:
            log.info('Old socket expired. Creating new one.')
            self._poller.unregister(self._sock)
            self._sock.close()

        self._sock = self._context.socket(zmq.REQ)
        self._sock.linger = 0
        self._sock.connect(self._broker)
        self._poller.register(self._sock, zmq.POLLIN)

    def _send(self, message):
        if not isinstance(message, list):
            message = [message]

        message = [CLIENT, self._service] + message

        log.debug('Sending to broker', message=message)

        reply = None

        retries = self._retries
        while retries > 0:
            self._sock.send_multipart(message)

            try:
                items = self._poller.poll(self._timeout)
            except KeyboardInterrupt:
                break

            if items:
                message = self._sock.recv_multipart()

                log.debug('Received reply', message=message)

                assert len(message) >= 3

                header = message.pop(0)
                assert header == CLIENT

                service = message.pop(0)
                assert service == self._service

                reply = message
                break
            else:
                if retries:
                    log.warn('No reply, reconnecting')
                    self._connect_to_broker()
                else:
                    log.error('No reply. No retries left. Abandoning')
                    break

                retries -= 1

        return reply

    def __getattr__(self, attr_name):
        if not hasattr(self._wrapped_cls, attr_name):
            raise AttributeError(
                'Remote {} instance has no attribute \'{}\''.
                format(self._wrapped_cls, attr_name)
            )

        def remote_call(*args, **kwargs):
            log.debug(
                'Calling remote procedure',
                cls=self._service,
                attr=attr_name,
                args=args,
                kwargs=kwargs
            )

            to_send = pickle.dumps((self._service, attr_name, args, kwargs))
            resp = self._send(to_send)

            assert resp == None or len(resp) == 1

            if resp is not None:
                resp = pickle.loads(resp[0])

                if isinstance(resp, Exception):
                    raise resp
                else:
                    return resp
            else:
                raise TimeoutException()

        if callable(getattr(self._wrapped_cls, attr_name)):
            return remote_call
        else:
            return remote_call()


class ServiceClient(Client):
    def __init__(self, broker):
        super(ServiceClient, self).__init__(broker, type('None'))

        self._service = b'icc'

    def __getattr__(self, name):
        resp = self._send([bytes(name, 'utf8')])
        return pickle.loads(resp[0])
