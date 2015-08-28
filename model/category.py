from sqlalchemy import Column, Integer, String

from . import Base


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    color = Column(String)
