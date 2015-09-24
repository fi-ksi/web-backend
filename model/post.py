import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, text
from sqlalchemy.types import TIMESTAMP

from . import Base
from thread import Thread

class Post(Base):
	__tablename__ = 'posts'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	thread = Column(Integer, ForeignKey(Thread.id))
	body = Column(Text, nullable=False)
	published_at = Column(TIMESTAMP, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))
	author = Column(Integer,)
	parent = Column(Integer, ForeignKey(__tablename__ + '.id'))
