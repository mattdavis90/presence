import logging
import sys

import structlog

import presence.log
from presence.config import Config
from presence.default_config import default_config

__version__ = '0.1.0'
__app_name__ = 'presence'
__banner__ = """\
  ______
 (_____ \\
  _____) )__ ____  ___  ____ ____   ____ ____
 |  ____/ __) _  )/___)/ _  )  _ \ / ___) _  )
 | |   | | ( (/ /|___ ( (/ /| | | ( (__( (/ /
 |_|   |_|  \____)___/ \____)_| |_|\____)____) v{}
""".format(__version__)

config = Config(default_config)
