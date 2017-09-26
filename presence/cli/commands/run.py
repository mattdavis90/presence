import click
import structlog

from click_didyoumean import DYMGroup

from presence import config
from presence.cli import cli
from presence.rpc import Broker, Client, Worker, ServiceClient
from presence.tasks.registry import Registry

log = structlog.getLogger()


@cli.group(cls=DYMGroup)
def run():
    pass


@run.command()
def broker():
    """Run the broker"""
    port = config['port']
    bind = 'tcp://*:{}'.format(port)

    log.info('Broker starting...', bind=bind)

    broker = Broker(bind)
    broker.start()


@run.command()
def registry():
    """Run the registry"""
    broker = config['broker']
    port = config['port']
    connect = 'tcp://{}:{}'.format(broker, port)

    log.info('Running Registry...', connect=connect)

    worker = Worker(connect, Registry())
    worker.start()


@run.command()
def test():
    """Test the registry"""
    broker = config['broker']
    port = config['port']
    connect = 'tcp://{}:{}'.format(broker, port)

    log.info('Testing Registry...', connect=connect)

    reg = Client(connect, Registry)
    from time import time
    start = time()
    for _ in range(10000):
        reg.register('test')
    end = time()
    log.info('10000 finished', time=(end - start))


@run.command()
def stats():
    """Get the broker stats"""
    from pprint import pprint as pp

    broker = config['broker']
    port = config['port']
    connect = 'tcp://{}:{}'.format(broker, port)

    log.info('Getting stats...', connect=connect)

    service_client = ServiceClient(connect)
    stats = service_client.stats()

    pp(stats)

    for worker in stats['workers']:
        print(worker)
        pp(service_client.worker_stats(worker))
