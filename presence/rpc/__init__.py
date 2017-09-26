CLIENT = b'client'
DISCONNECT = b'disconnect'
HEARTBEAT = b'heartbeat'
READY = b'ready'
REPLY = b'reply'
REQUEST = b'request'
STATS = b'stats'
WORKER = b'worker'
WORKER_STATS = b'worker_stats'


class RPCException(Exception):
    pass


class TimeoutException(RPCException):
    pass


from .broker import Broker  # noqa
from .worker import Worker  # noqa
from .client import Client, ServiceClient  # noqa
