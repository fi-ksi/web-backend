import datetime

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey

from . import Base
from .user import User


class UserNotify(Base):
    __tablename__ = 'users_notify'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    user = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                  primary_key=True)
    auth_token = Column(String(255), nullable=False)
    notify_eval = Column(Boolean, nullable=False, default=True)
    notify_response = Column(Boolean, nullable=False, default=True)
    notify_ksi = Column(Boolean, nullable=False, default=True)
    notify_events = Column(Boolean, nullable=False, default=True)
