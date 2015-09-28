from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, Boolean, ForeignKey, text

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
	name = Column(String(255), nullable=False)
	description = Column(Text)
	max_points = Column(Integer, nullable=False)
	autocorrect = Column(Boolean, nullable=False, default=False, server_default=text('FALSE'))
	order = Column(SmallInteger, nullable=False, default=1, server_default='1')
