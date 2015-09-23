
import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from . import Base


class Token(Base):
    __tablename__ = 'oauth2_tokens'
    access = Column(String, primary_key=True)
    expire = Column(Integer)
    granted = Column(DateTime, default=datetime.datetime.utcnow)
    refresh = Column(String)
    id_user = Column(Integer, ForeignKey('users.id'))
