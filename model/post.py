import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

from . import Base
from thread import Thread
from user import User

class Post(Base):
	__tablename__ = 'posts'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	thread = Column(Integer, ForeignKey(Thread.id, ondelete='CASCADE'), nullable=False)
	author = Column(Integer, ForeignKey(User.id), nullable=False)
	body = Column(Text, nullable=False)
	published_at = Column(TIMESTAMP, nullable=False, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))
	parent = Column(Integer, ForeignKey(__tablename__ + '.id', ondelete='CASCADE'))

	reactions = relationship('Post')
