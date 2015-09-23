import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from . import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name_first = Column(String)
    name_last = Column(String)
    name_nick = Column(String)
    password = Column(String)
    admin = Column(Boolean, default=False)
    time_created = Column(DateTime, default=datetime.datetime.utcnow)

    child = relationship('Token', uselist=False, backref='owner')
