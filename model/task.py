import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from . import Base

class Task(Base):
	__tablename__ = 'tasks'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	title = Column(String(255), nullable=False)
	author = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
	wave = Column(Integer, ForeignKey('waves.id'), nullable=False)
	category = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
	prerequisite = Column(Integer, ForeignKey('prerequisities.id'), nullable=True)
	intro = Column(String(500), nullable=False)
	body = Column(Text, nullable=False)
	solution = Column(Text, nullable=True)
	position_x = Column(Integer, nullable=False, default=0, server_default="0")
	position_y = Column(Integer, nullable=False, default=0, server_default="0")
	thread = Column(Integer, ForeignKey('threads.id'), nullable=False)
	picture_base = Column(String(255), nullable=False)
	time_created = Column(DateTime, default=datetime.datetime.utcnow)
	time_published = Column(DateTime, default=datetime.datetime.utcnow)
	time_deadline = Column(DateTime, default=datetime.datetime.utcnow)

	prerequisite_obj = relationship('Prerequisite', primaryjoin='Task.prerequisite==Prerequisite.id', uselist=False)
	modules = relationship('Module', primaryjoin='Task.id==Module.task', order_by='Module.order')
	solution_public = Column(Boolean, nullable=False)

class SolutionComment(Base):
	__tablename__ = 'solution_comments'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	thread = Column(Integer, ForeignKey('threads.id'), nullable=False, primary_key=True)
	user = Column(Integer, ForeignKey('users.id'), nullable=False, primary_key=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=False, primary_key=True)

