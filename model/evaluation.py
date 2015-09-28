import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, ForeignKey, text
from sqlalchemy.types import TIMESTAMP

from . import Base

class Evaluation(Base):
	__tablename__ = 'evaluations'
	__table_args__ = (
		{
			'mysql_engine': 'InnoDB',
			'mysql_charset': 'utf8',
		})

	id = Column(Integer, primary_key=True)
	user = Column(Integer, ForeignKey('users.id'), nullable=False)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	evaluator = Column(Integer, ForeignKey('users.id'))
	points = Column(Integer, nullable=False, default=0, server_default='0')
	comment = Column(Text)
	full_report = Column(Text)
	time = Column(TIMESTAMP, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))