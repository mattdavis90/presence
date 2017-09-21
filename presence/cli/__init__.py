import errno
import logging
import os
import sys

import click
import structlog

from click_didyoumean import DYMGroup
from click_repl import repl
from prompt_toolkit.history import FileHistory

from presence import __app_name__, __banner__, config
from presence.cli.utils import handle_log_level

log = structlog.getLogger()


@click.group(cls=DYMGroup, invoke_without_command=True)
@click.argument('config_file', type=click.Path(exists=True))
@click.option(
    '--log-level',
    default='INFO',
    metavar='LEVEL',
    callback=handle_log_level,
    help='Either CRITICAL, ERROR, WARNING, INFO or DEBUG'
)
def cli(config_file, log_level):
    logging.getLogger().setLevel(log_level)

    config.read(config_file)

    config_dir = os.path.join(click.get_app_dir(__app_name__))

    log.debug('Creating application directory "{}"'.format(config_dir))

    try:
        os.makedirs(config_dir)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(config_dir):
            pass
        else:
            log.critical(
                'Cannot create application directory "{}"'.format(config_dir)
            )
            sys.exit(1)

    click.clear()
    click.secho(__banner__, bold=True)

    ctx = click.get_current_context()

    if ctx.invoked_subcommand is None:
        prompt_kwargs = {
            'history':
            FileHistory(
                os.path.join(click.get_app_dir(__app_name__), 'history')
            ),
            'message':
            'Presence> ',
        }
        repl(ctx, prompt_kwargs=prompt_kwargs)


import presence.cli.commands  # noqa
