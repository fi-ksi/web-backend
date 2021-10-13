import logging
from logging import Logger


def get_log() -> Logger:
    """
    Gets the default Logger logging instance for the application
    """
    return logging.getLogger('gunicorn.error')
