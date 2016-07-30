import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, text, Boolean
from sqlalchemy.types import TIMESTAMP

from . import Base
from year import Year

class Article(Base):
	__tablename__ = 'articles'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True, nullable=False)
	author = Column(Integer, ForeignKey('users.id'), nullable=False)
	title = Column(String(255), nullable=False)
	body = Column(Text)
	picture = Column(String(255))
	time_created = Column(TIMESTAMP, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))
	published = Column(Boolean)
	year = Column(Integer, ForeignKey(Year.id), nullable=False)
	resource = Column(String(512), nullable=True)
