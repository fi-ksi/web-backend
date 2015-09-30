from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from . import Base

class PrerequisiteType:
	ATOMIC = 'ATOMIC'
	AND = 'AND'
	OR = 'OR'

class Prerequisite(Base):
	__tablename__ = 'prerequisities'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	type = Column(Enum(PrerequisiteType.ATOMIC, PrerequisiteType.AND, PrerequisiteType.OR), nullable=False, default=PrerequisiteType.ATOMIC, server_default=PrerequisiteType.ATOMIC)
	parent = Column(Integer, ForeignKey(__tablename__ + '.id'), nullable=True)
	task = Column(Integer, ForeignKey('tasks.id'), nullable=True)

	children = relationship('Prerequisite', primaryjoin='Prerequisite.parent == Prerequisite.id')