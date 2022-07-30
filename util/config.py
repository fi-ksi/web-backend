import os
from typing import Optional

from sqlalchemy import func

from db import session
import model

MAX_UPLOAD_FILE_SIZE = 20 * 10**6
MAX_UPLOAD_FILE_COUNT = 20


def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a property from the config table in database
    If key does not exist, then default value is returned
    :param key: key to get value for
    :param default: default value in case the key does not exist
    :return: value in database if the key exists, default otherwise
    """
    prop = session.query(model.Config).get(key)
    return prop.value if prop is not None else default


def ksi_conf():
    return get("ksi_conf")


def mail_sign():
    return get("mail_sign")


def ksi_web():
    return get("web_url")


def mail_sender() -> Optional[str]:
    """
    Get the default mail sender
    """
    return get("mail_sender")


def backend_url():
    return get("backend_url")

def monitoring_dashboard_url():
    return get("monitoring_dashboard_url")

def feedback():
    return [r for r, in session.query(model.FeedbackRecipient.email).all()]
