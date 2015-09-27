from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship

from . import Base

class Sortable(Base):
	__tablename__ = 'sortables'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	type = Column(Enum('fixed', 'movable'), nullable=False)
	content = Column(String(255), nullable=False)
	style = Column(String(255))
	correct_position = Column(SmallInteger, nullable=False)
	order = Column(SmallInteger, nullable=False, default=1, server_default='1')
