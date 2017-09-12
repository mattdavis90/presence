import click
import structlog

from click_didyoumean import DYMGroup

from presence.cli import cli
from presence.tasks.registry import Registry
from presence.tasks.utils import make_remote, remote_runner


log = structlog.getLogger()


@cli.group(cls=DYMGroup)
def run():
    pass


@run.command()
def registry():
    """Run the registry"""
    log.info('Running Registry...')
    reg = Registry()
    remote_runner(reg, 'tcp://*:5000')


@run.command()
def test():
    reg = make_remote(Registry, 'tcp://registry:5000')
    log.info('Result', ans=reg.register('test'))
    log.info('Result', ans=reg.test())
