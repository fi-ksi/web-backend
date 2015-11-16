import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Interval, func
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from . import Base

class Token(Base):
	__tablename__ = 'oauth2_tokens'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	access_token = Column(String(255), primary_key=True)
	user = Column(Integer, ForeignKey('users.id'))
	expire = Column(DateTime, default=datetime.timedelta(hours=1))
	refresh_token = Column(String(255))
	granted = Column(DateTime, default=datetime.datetime.utcnow)

