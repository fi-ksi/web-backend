from sqlalchemy import Column, Integer, String, Text, ForeignKey

from . import Base

class Programming(Base):
	__tablename__ = 'programming'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	default_code = Column(Text, nullable=True)
