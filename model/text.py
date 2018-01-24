from sqlalchemy import Column, Integer, String, Text, ForeignKey, text, Boolean
from sqlalchemy.types import TIMESTAMP
import datetime

from . import Base
from .module import Module


class Text(Base):
    __tablename__ = 'text'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4',
    }

    id = Column(Integer, primary_key=True)
    module = Column(Integer, ForeignKey(Module.id), nullable=False)
    inputs = Column(Integer)
    diff = Column(Text)
    ignore_case = Column(Boolean)
    eval_script = Column(String(255))
