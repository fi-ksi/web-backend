from sqlalchemy import Column, Integer, String, Text, ForeignKey, text
from sqlalchemy.types import TIMESTAMP
import datetime

from . import Base

class CodeExecution(Base):
	__tablename__ = 'code_executions'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	user = Column(Integer, ForeignKey('users.id'), nullable=False)
	code = Column(Text)
	time = Column(TIMESTAMP, default=datetime.datetime.utcnow(), server_default=text('CURRENT_TIMESTAMP'))
