from sqlalchemy import Column, Integer, String

from . import Base


class Thread(Base):
    __tablename__ = 'threads'
    id = Column(Integer, primary_key=True)
    title = Column(String)
