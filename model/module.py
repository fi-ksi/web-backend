from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, Boolean, ForeignKey, text, DECIMAL

from . import Base
from task import Task

class ModuleType(Enum):
    GENERAL = "general"
    PROGRAMMING = "programming"
    QUIZ = "quiz"
    SORTABLE = "sortable"
    TEXT = "text"

class Module(Base):
    __tablename__ = 'modules'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
    }

    id = Column(Integer, primary_key=True)
    task = Column(Integer, ForeignKey(Task.id, ondelete='CASCADE'), nullable=False)
    type = Column(Enum(ModuleType.GENERAL, ModuleType.PROGRAMMING, ModuleType.QUIZ, ModuleType.SORTABLE, ModuleType.TEXT), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    max_points = Column(DECIMAL(precision=10, scale=1, asdecimal=False), nullable=False, default=0)
    autocorrect = Column(Boolean, nullable=False, default=False, server_default=text('FALSE'))
    order = Column(SmallInteger, nullable=False, default=1, server_default='1')
    bonus = Column(Boolean, nullable=False, default=False, server_default=text('FALSE'))
    action = Column(Text)
    data = Column(Text)

