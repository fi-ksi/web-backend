import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

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
	garant = Column(Integer, ForeignKey('users.id'), nullable=False)
	time_published = Column(DateTime, default=datetime.datetime.utcnow)
	
	@hybrid_property
	def public(self):
		return self.time_published <= datetime.datetime.utcnow()

