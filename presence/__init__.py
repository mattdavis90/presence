import logging
import sys

import structlog

import presence.log # noqa


__version__ = '0.1.0'
__app_name__ = 'presence'
__banner__ = """\
  ______
 (_____ \\
  _____) )___ ____  ___  ____ ____   ____ ____
 |  ____/ ___) _  )/___)/ _  )  _ \ / ___) _  )
 | |   | |  ( (/ /|___ ( (/ /| | | ( (__( (/ /
 |_|   |_|   \____|___/ \____)_| |_|\____)____) v{}
""".format(__version__)
