import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship

from . import Base
from user import User
from thread import Thread
from wave import Wave

class Task(Base):
	__tablename__ = 'tasks'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	title = Column(String(255), nullable=False)
	author = Column(Integer, ForeignKey(User.id), nullable=True)
	wave = Column(Integer, ForeignKey(Wave.id), nullable=False)
	prerequisite = Column(Integer, ForeignKey('prerequisities.id', ondelete='SET NULL'), nullable=True)
	intro = Column(String(500), nullable=False, default="")
	body = Column(Text, nullable=False, default="")
	solution = Column(Text, nullable=True)
	thread = Column(Integer, ForeignKey(Thread.id), nullable=False)
	picture_base = Column(String(255), nullable=True)
	time_created = Column(DateTime, default=datetime.datetime.utcnow)
	time_deadline = Column(DateTime, default=datetime.datetime.utcnow)

	prerequisite_obj = relationship('Prerequisite', primaryjoin='Task.prerequisite==Prerequisite.id', uselist=False)
	modules = relationship('Module', primaryjoin='Task.id==Module.task', order_by='Module.order')
	evaluation_public = Column(Boolean, nullable=False, default=False)

	git_path = Column(String(255), nullable=True)
	git_branch = Column(String(255), nullable=True)
	git_commit = Column(String(255), nullable=True)
	deploy_date = Column(DateTime, nullable=True, default=None)
	deploy_status = Column(Enum('default', 'deploying', 'done', 'error', 'diff'), nullable=False, default='default')

class SolutionComment(Base):
	__tablename__ = 'solution_comments'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	thread = Column(Integer, ForeignKey('threads.id'), nullable=False, primary_key=True)
	user = Column(Integer, ForeignKey('users.id'), nullable=False, primary_key=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=False, primary_key=True)

