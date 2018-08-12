from sqlalchemy import Column, Integer, ForeignKey, Text, text
from sqlalchemy.types import TIMESTAMP
import datetime

from . import Base
from .user import User
from .task import Task


class Feedback(Base):
    __tablename__ = 'feedbacks'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    user = Column(
        Integer,
        ForeignKey(User.id, ondelete='CASCADE', onupdate='NO ACTION'),
        primary_key=True,
        nullable=False,
    )
    task = Column(
        Integer,
        ForeignKey(Task.id, ondelete='CASCADE', onupdate='NO ACTION'),
        primary_key=True,
        nullable=False,
    )
    content = Column(Text, nullable=False)
    lastUpdated = Column(TIMESTAMP, default=datetime.datetime.utcnow,
                         server_default=text('CURRENT_TIMESTAMP'))
