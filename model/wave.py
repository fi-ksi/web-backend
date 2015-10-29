import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean

from . import Base

class Wave(Base):
	__tablename__ = 'waves'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True, nullable=False)
	year = Column(Integer, ForeignKey('years.id'), nullable=False)
	index = Column(Integer, nullable=False)
	caption = Column(String(100), nullable=True)
	public = Column(Boolean, nullable=False, default=0, server_default='0')

