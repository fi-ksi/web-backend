from sqlalchemy import Column, Integer, String

from . import Base

class Achievement(Base):
	__tablename__ = 'achievements'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	title = Column(String(255), nullable=False)
	code = Column(String(10), nullable=False, unique=True)
