import json
import logging
from logging import Logger
from typing import Optional

from db import session
from model.audit_log import AuditLog


def get_log() -> Logger:
    """
    Gets the default Logger logging instance for the application
    """
    return logging.getLogger('gunicorn.error')


def audit_log(scope: str, user_id: Optional[int], message: str, message_meta: Optional[dict] = None, year_id: Optional[int] = None) -> None:
    log_db = AuditLog(
        scope=scope,
        user_id=user_id,
        year_id=year_id,
        line=message,
        line_meta=json.dumps(message_meta) if message_meta else None
    )
    get_log().warning(f"[AUDIT] [{scope}] [{user_id}]: {message}")
    session.add(log_db)
    session.commit()
