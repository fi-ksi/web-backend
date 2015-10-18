from sqlalchemy import Column, Integer, String, Text, ForeignKey, text, Boolean
from sqlalchemy.types import TIMESTAMP
import datetime

from . import Base

class Text(Base):
	__tablename__ = 'text'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	inputs = Column(Integer)
	diff = Column(Text)
	ignore_case = Column(Boolean)
	eval_script = Column(String(255))
