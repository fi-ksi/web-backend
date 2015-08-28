from sqlalchemy import Column, Integer, String

from . import Base


class Achievement(Base):
    __tablename__ = 'achievements'
    id = Column(Integer, primary_key=True)
    title = Column(String)
