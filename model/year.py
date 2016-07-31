import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean

from . import Base

class Year(Base):
	__tablename__ = 'years'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True, nullable=False)
	year = Column(String(100), nullable=True)
	sealed = Column(Boolean, nullable=False, default=False)

