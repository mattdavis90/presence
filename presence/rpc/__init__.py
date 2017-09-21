CLIENT = b'client'
WORKER = b'worker'
READY = b'ready'
REPLY = b'reply'
REQUEST = b'request'
DISCONNECT = b'disconnect'
HEARTBEAT = b'heartbeat'


class RPCException(Exception):
    pass


class TimeoutException(RPCException):
    pass


from .broker import Broker  # noqa
from .worker import Worker  # noqa
from .client import Client, ServiceClient  # noqa
