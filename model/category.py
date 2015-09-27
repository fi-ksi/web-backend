from sqlalchemy import Column, Integer, String

from . import Base


class Category(Base):
	__tablename__ = 'categories'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	type = Column(String(255), nullable=False)
	color = Column(String(20))
