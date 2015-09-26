import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

from . import Base

class User(Base):
	__tablename__ = 'users'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	email = Column(String(255), nullable=False, unique=True)
	phone = Column(String(15))
	first_name = Column(String(255), nullable=False)
	last_name = Column(String(255), nullable=False)
	sex = Column(Enum('male', 'female'), nullable=False)
	password = Column(String(255), nullable=False)
	role = Column(Enum('admin', 'org', 'participant'), nullable=False, default='participant', server_default='participant')
	enabled = Column(Integer, nullable=False, default=1, server_default='1')
	registered = Column(TIMESTAMP, nullable=False, default=datetime.datetime.utcnow, server_default=text('CURRENT_TIMESTAMP'))

	#child = relationship('Token', uselist=False, backref='owner')
