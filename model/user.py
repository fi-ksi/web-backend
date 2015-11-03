import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Text, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

from . import Base
from user_achievement import UserAchievement

class User(Base):
	__tablename__ = 'users'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(Integer, primary_key=True)
	email = Column(String(50), nullable=False, unique=True)
	phone = Column(String(15))
	first_name = Column(String(50), nullable=False)
	nick_name = Column(String(50))
	last_name = Column(String(50), nullable=False)
	sex = Column(Enum('male', 'female'), nullable=False)
	password = Column(String(255), nullable=False)
	short_info = Column(Text, nullable=False)
	profile_picture = Column(String(255))
	role = Column(Enum('admin', 'org', 'participant'), nullable=False, default='participant', server_default='participant')
	enabled = Column(Integer, nullable=False, default=1, server_default='1')
	registered = Column(TIMESTAMP, nullable=False, default=datetime.datetime.now, server_default=text('CURRENT_TIMESTAMP'))

	achievements = relationship("Achievement", secondary=UserAchievement.__tablename__)
	tasks = relationship("Task", primaryjoin='User.id == Task.author')

	#child = relationship('Token', uselist=False, backref='owner')
