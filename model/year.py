import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey

from . import Base

class Article(Base):
	__tablename__ = 'years'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True, nullable=False)
	year = Column(String(100), nullable=True)

