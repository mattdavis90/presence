import click
import structlog

from click_didyoumean import DYMGroup

from presence import config
from presence.cli import cli
from presence.rpc import Broker, Client, Worker, ServiceClient
from presence.tasks.store import Store

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
@click.option('-i', '--identifier', default='')
def store(identifier):
    """Run the store"""
    broker = config['broker']
    port = config['port']
    connect = 'tcp://{}:{}'.format(broker, port)

    log.info('Running Store...', connect=connect)

    worker = Worker(connect, Store(), service_suffix=identifier)
    worker.start()


@run.command()
@click.option('-i', '--identifier', default='')
def test(identifier):
    """Test the store"""
    broker = config['broker']
    port = config['port']
    connect = 'tcp://{}:{}'.format(broker, port)

    log.info('Testing Store...', connect=connect)

    store = Client(connect, Store, service_suffix=identifier)
    from time import time
    start = time()
    for _ in range(1000):
        store.add_dhcp('00:11:22:33:44:55', '192.168.1.1', 'localhost')
    end = time()
    log.info('1000 finished', time=(end - start))


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
