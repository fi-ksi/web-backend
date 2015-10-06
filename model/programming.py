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
	default_code = Column(Text)
	merge_script = Column(String(255))
	stdin = Column(String(255))
	args = Column(String(255))
	timeout = Column(Integer)
	check_script = Column(String(255))
