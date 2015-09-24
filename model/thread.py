from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from . import Base

class Thread(Base):
	__tablename__ = 'threads'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	title = Column(String(1000))
