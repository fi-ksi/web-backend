from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, UniqueConstraint

from . import Base

class Module(Base):
	__tablename__ = 'modules'
	__table_args__ = (
		UniqueConstraint('task', 'type', name='_task_type_uc'),
		{
			'mysql_engine': 'InnoDB',
			'mysql_charset': 'utf8',
		})

	id = Column(Integer, primary_key=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=False)
	type = Column(Enum('general', 'programming', 'quiz', 'sortable'), nullable=False)
	description = Column(Text)
