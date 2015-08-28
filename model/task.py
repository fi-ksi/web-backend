import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey

from . import Base


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    position_x = Column(Integer)
    position_y = Column(Integer)
    title = Column(String)
    body = Column(Text)
    max_score = Column(Integer)
    time_created = Column(DateTime, default=datetime.datetime.utcnow)
    time_published = Column(DateTime, default=datetime.datetime.utcnow)
    time_deadline = Column(DateTime, default=datetime.datetime.utcnow)

    id_author = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'),
                       nullable=True,)
    id_category = Column(Integer,
                         ForeignKey('categories.id', ondelete='SET NULL'),
                         nullable=True,)
