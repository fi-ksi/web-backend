from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from . import Base

class Prerequisite(Base):
	__tablename__ = 'prerequisities'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	type = Column(Enum('ATOMIC', 'AND', 'OR'), nullable=False, default='ATOMIC', server_default='ATOMIC')
	parent = Column(Integer, ForeignKey(__tablename__ + '.id'), nullable=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=True)

	children = relationship('Prerequisite', primaryjoin='Prerequisite.parent == Prerequisite.id')