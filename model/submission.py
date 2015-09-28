import datetime
from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, ForeignKey, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

from . import Base

class Submission(Base):
	__tablename__ = 'submissions'
	__table_args__ = (
		{
			'mysql_engine': 'InnoDB',
			'mysql_charset': 'utf8',
		})

	id = Column(Integer, primary_key=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=False)
	user = Column(Integer, ForeignKey('users.id'), nullable=False)
	time = Column(TIMESTAMP, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))

	evaluations = relationship('Evaluation', primaryjoin='Submission.id==Evaluation.submission')
