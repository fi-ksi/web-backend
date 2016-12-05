import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, ForeignKey, text, DECIMAL, Boolean
from sqlalchemy.types import TIMESTAMP

from . import Base
from user import User
from module import Module

class Evaluation(Base):
    __tablename__ = 'evaluations'
    __table_args__ = (
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8',
        })

    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'), nullable=False)
    module = Column(Integer, ForeignKey(Module.id), nullable=False)
    evaluator = Column(Integer, ForeignKey(User.id))
    points = Column(DECIMAL(precision=10, scale=1, asdecimal=False), nullable=False, default=0)
    ok = Column(Boolean, nullable=False, default=False, server_default=text('FALSE'))
    full_report = Column(Text, nullable=False, default="")
    time = Column(TIMESTAMP, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))
