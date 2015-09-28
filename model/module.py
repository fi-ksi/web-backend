from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, ForeignKey

from . import Base

class Module(Base):
	__tablename__ = 'modules'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=False)
	type = Column(Enum('general', 'programming', 'quiz', 'sortable'), nullable=False)
	description = Column(Text)
	points = Column(Integer, nullable=False)
	order = Column(SmallInteger, nullable=False, default=1, server_default='1')
