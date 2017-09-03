import click
import structlog

from celery.worker.worker import WorkController
from click_didyoumean import DYMGroup

from presence import celery_app
from presence.cli import cli


log = structlog.getLogger()


@cli.group(cls=DYMGroup)
def worker():
    pass


@worker.command()
def syslog():
    """Run the syslog worker"""
    log.info('Starting syslog celery worker...')
    WorkController(celery_app).start()
