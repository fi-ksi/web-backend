import os
from typing import Optional, List

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


def ksi_conf() -> Optional[str]:
    return get("ksi_conf")


def mail_sign() -> Optional[str]:
    return get("mail_sign")


def ksi_web() -> Optional[str]:
    """
    Get the root URL of the frontend website
    :return: root URL of the frontend website
    """
    return get("web_url")


def mail_sender() -> Optional[str]:
    """
    Get the default mail sender
    """
    return get("mail_sender")


def successful_participant_trophy_id() -> Optional[int]:
    text = get('successful_participant_trophy_id')
    return int(text) if text is not None else None


def backend_url() -> Optional[str]:
    return get("backend_url")


def monitoring_dashboard_url() -> Optional[str]:
    return get("monitoring_dashboard_url")


def github_token() -> Optional[str]:
    """
    Get the OAuth2.0 personal access token for fi-ksi-admin GitHub account

    This token can be used for making requests to the GitHub API
    """
    return get("github_token")


def seminar_repo() -> Optional[str]:
    """
    Get the name of the seminar repository that contains tasks
    """
    return get("seminar_repo")


def feedback() -> List[str]:
    return [r for r, in session.query(model.FeedbackRecipient.email).all()]


def discord_username_change_webhook() -> Optional[str]:
    """
    Get the webhook URL for Discord that should be called whenever a user changes their Discord username

    :return webhook URL for Discord that should be called whenever a user changes their Discord username
    """
    return get("webhook_discord_username_change")


def discord_invite_link() -> Optional[str]:
    """
    Get the invite link to the Discord server

    :return the invite link to the Discord server
    """
    return get("discord_invite_link")
