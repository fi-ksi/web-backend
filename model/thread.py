import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship

from sqlalchemy.types import TIMESTAMP

from . import Base
from .year import Year
from .user import User


class Thread(Base):
    __tablename__ = 'threads'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True)
    title = Column(String(1000))
    public = Column(Boolean, nullable=False, default=True,
                    server_default=text('TRUE'))
    year = Column(Integer, ForeignKey(Year.id), nullable=False)

    posts = relationship('Post', backref="Thread",
                         primaryjoin="Post.thread==Thread.id")


class ThreadVisit(Base):
    __tablename__ = 'threads_visits'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    thread = Column(Integer, ForeignKey(Thread.id, ondelete='CASCADE'),
                    primary_key=True, nullable=False)
    user = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                  primary_key=True, nullable=False)
    last_visit = Column(TIMESTAMP, nullable=False,
                        default=datetime.datetime.utcnow,
                        server_default=text('CURRENT_TIMESTAMP'))
    last_last_visit = Column(TIMESTAMP, nullable=True)
