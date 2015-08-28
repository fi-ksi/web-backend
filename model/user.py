import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean

from . import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name_first = Column(String, nullable=False)
    name_last = Column(String, nullable=False)
    name_nick = Column(String, nullable=False)
    admin = Column(Boolean, default=False, nullable=False)
    time_created = Column(DateTime, default=datetime.datetime.utcnow,
                          nullable=False)
