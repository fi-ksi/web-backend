import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from . import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(Text)
    time_created = Column(DateTime, default=datetime.datetime.utcnow)
