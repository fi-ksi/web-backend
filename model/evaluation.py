from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, ForeignKey, UniqueConstraint

from . import Base

class Evaluation(Base):
	__tablename__ = 'evaluations'
	__table_args__ = (
		UniqueConstraint('submission', 'module', name='_submission_type_uc'),
		{
			'mysql_engine': 'InnoDB',
			'mysql_charset': 'utf8',
		})

	id = Column(Integer, primary_key=True)
	submission = Column(Integer, ForeignKey('submissions.id'), nullable=False)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	evaluator = Column(Integer, ForeignKey('users.id'))
	points = Column(Integer, nullable=False, default=0, server_default='0')
	comment = Column(Text)
	full_report = Column(Text)
