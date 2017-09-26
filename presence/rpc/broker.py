import pickle
from binascii import hexlify
from time import time

import structlog
import zmq.green as zmq

from .. import config
from . import CLIENT, DISCONNECT, HEARTBEAT, READY, REPLY, REQUEST, STATS, WORKER, WORKER_STATS
from .utils import get_usage

log = structlog.getLogger()


class Worker(object):
    def __init__(self, identity, address, lifetime):
        self.identity = identity
        self.address = address
        self.service = None
        self.expiry = time() + 1e-3 * lifetime


class Service(object):
    def __init__(self, name):
        self.name = name
        self.requests = []
        self.waiting_workers = []


class Broker(object):
    def __init__(self, bind):
        self._heartbeat_count = config['heartbeat_count']
        self._heartbeat_interval = config['heartbeat_interval']
        self._control_service = config['control_service']

        self._heartbeat_expiry = self._heartbeat_count * self._heartbeat_interval
        self._heartbeat_at = time() + 1e-3 * self._heartbeat_interval

        self._workers = {}
        self._waiting_workers = []
        self._services = {}

        context = zmq.Context()

        self._sock = context.socket(zmq.ROUTER)
        self._sock.linger = 0
        self._sock.bind(bind)

        log.info('Broker listening', bind=bind)

        self._poller = zmq.Poller()
        self._poller.register(self._sock, zmq.POLLIN)

    def start(self):
        while True:
            try:
                items = self._poller.poll(self._heartbeat_interval)
            except KeyboardInterrupt:
                break

            if items:
                message = self._sock.recv_multipart()

                log.debug('Got a message', message=message)

                sender = message.pop(0)
                empty = message.pop(0)
                assert empty == b''

                header = message.pop(0)

                if header == CLIENT:
                    self._handle_client(sender, message)
                elif header == WORKER:
                    self._handle_worker(sender, message)
                else:
                    log.error('Invalid message')

            self._purge_workers()
            self._send_heartbeats()

    def _handle_worker(self, sender, message):
        assert len(message) >= 1

        command = message.pop(0)

        worker_ready = hexlify(sender) in self._workers
        worker = self._get_worker(sender)

        if command == READY:
            assert len(message) >= 1

            service = message.pop(0)

            if worker_ready or service == self._control_service:
                self._delete_worker(worker, True)
            else:
                worker.service = self._get_service(service)
                self._worker_is_waiting(worker)
        elif command == REPLY:
            if worker_ready:
                client = message.pop(0)
                empty = message.pop(0)
                assert empty == b''

                message = [client, b'', CLIENT, worker.service.name] + message

                self._sock.send_multipart(message)
                self._worker_is_waiting(worker)
            else:
                self._delete_worker(worker, True)
        elif command == HEARTBEAT:
            if worker_ready:
                worker.expiry = time() + 1e-3 * self._heartbeat_expiry
            else:
                self._delete_worker(worker, True)
        elif command == DISCONNECT:
            self._delete_worker(worker, False)
        else:
            log.error("Invalid message", message=message)

    def _handle_client(self, sender, message):
        assert len(message) >= 2

        service = message.pop(0)

        message = [sender, b''] + message

        if service == self._control_service:
            self._handle_control(service, message)
        else:
            self._dispatch(self._get_service(service), message)

    def _handle_control(self, service, message):
        assert len(message) >= 3

        client = message.pop(0)

        empty = message.pop(0)
        assert empty == b''

        command = message.pop(0)

        # Command handling should pop params from message
        # and, send a pickled response in reply... or set
        # reply to None to ignore message - you must be
        # sure that something will respond or the client
        # will timeout
        reply = pickle.dumps(None)

        if command == STATS:
            stats = {}

            stats['workers'] = [name for name in self._workers.keys()]
            stats['waiting_workers'] = [
                worker.identity for worker in self._waiting_workers
            ]
            stats['services'] = {}
            for svc in self._services.values():
                stats['services'][svc.name] = len(svc.requests)
            stats['usage'] = get_usage()

            reply = pickle.dumps(stats)
        elif command == WORKER_STATS:
            identity = message.pop(0)
            worker = self._workers.get(identity)

            if worker:
                self._send_to_worker(worker, STATS, message=client)
                reply = None

        if reply:
            message = [client, b'', CLIENT, service, reply]
            self._sock.send_multipart(message)

    def _get_worker(self, address):
        assert address is not None

        identity = hexlify(address)

        worker = self._workers.get(identity, None)

        if worker is None:
            worker = Worker(identity, address, self._heartbeat_expiry)
            self._workers[identity] = worker

            log.info('New worker', worker=identity)

        return worker

    def _delete_worker(self, worker, disconnect):
        assert worker is not None

        if disconnect:
            log.info('Disconnecting worker', worker=worker.identity)
            self._send_to_worker(worker, DISCONNECT)

        if worker.service is not None:
            worker.service.waiting_workers.remove(worker)

        self._workers.pop(worker.identity)

    def _worker_is_waiting(self, worker):
        if worker not in self._waiting_workers:
            self._waiting_workers.append(worker)

        if worker not in worker.service.waiting_workers:
            worker.service.waiting_workers.append(worker)

        worker.expiry = time() + 1e-3 * self._heartbeat_expiry

        self._dispatch(worker.service, None)

    def _purge_workers(self):
        self._waiting_workers = sorted(
            self._waiting_workers, key=lambda w: w.expiry
        )

        while self._waiting_workers:
            worker = self._waiting_workers[0]

            if worker.expiry < time():
                log.info('Expiring worker', worker=worker.identity)

                self._delete_worker(worker, False)
                self._waiting_workers.pop(0)
            else:
                break

    def _send_to_worker(self, worker, command, option=None, message=[]):
        if not isinstance(message, list):
            message = [message]

        if option is not None:
            message = [option] + message

        message = [worker.address, b'', WORKER, command] + message

        log.debug('Sending to worker', message=message)

        self._sock.send_multipart(message)

    def _get_service(self, name):
        assert name is not None

        service = self._services.get(name, None)

        if service is None:
            service = Service(name)
            self._services[name] = service

            log.info('New service', service=name)

        return service

    def _dispatch(self, service, message):
        assert service is not None

        if message is not None:
            service.requests.append(message)

        self._purge_workers()

        while service.waiting_workers and service.requests:
            message = service.requests.pop(0)
            worker = service.waiting_workers.pop(0)

            self._waiting_workers.remove(worker)
            self._send_to_worker(worker, REQUEST, message=message)

    def _send_heartbeats(self):
        if time() > self._heartbeat_at:
            for worker in self._waiting_workers:
                self._send_to_worker(worker, HEARTBEAT)

            self._heartbeat_at = time() + 1e-3 * self._heartbeat_interval
