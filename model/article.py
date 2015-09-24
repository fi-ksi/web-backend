import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, text
from sqlalchemy.types import TIMESTAMP

from . import Base

class Article(Base):
	__tablename__ = 'articles'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True, nullable=False)
	title = Column(String(255), nullable=False)
	body = Column(Text)
	picture = Column(String(255))
	time_created = Column(TIMESTAMP, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))

	#~ id_author = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"),
					   #~ nullable=True)
