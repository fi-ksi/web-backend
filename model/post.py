import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from . import Base


class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    body = Column(Text)
    time_created = Column(DateTime, default=datetime.datetime.utcnow)
