import logging

import click


def handle_log_level(ctx, param, value):
    level = logging.getLevelName(value.upper())

    if not isinstance(level, int):
        raise click.BadParameter('Must be CRITICAL, ERROR, WARNING, INFO or DEBUG, not "{}"'.format(value))

    return level
