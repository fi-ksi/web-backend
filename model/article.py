import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey

from . import Base


class Article(Base):
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    body = Column(Text)
    time_created = Column(DateTime, default=datetime.datetime.utcnow)

    id_author = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"),
                       nullable=True)
