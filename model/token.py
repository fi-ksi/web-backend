import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from . import Base

class Token(Base):
	__tablename__ = 'oauth2_tokens'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	access_token = Column(String(255), primary_key=True)
	user = Column(Integer, ForeignKey('users.id'))
	expire = Column(Integer)
	refresh_token = Column(String(255))
	granted = Column(DateTime, default=datetime.datetime.utcnow)
