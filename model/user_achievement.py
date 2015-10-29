from sqlalchemy import Column, Integer, ForeignKey

from . import Base

class UserAchievement(Base):
	__tablename__ = 'user_achievement'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	user_id = Column(Integer, ForeignKey('users.id'), primary_key=True, nullable=False)
	achievement_id = Column(Integer, ForeignKey('achievements.id'), primary_key=True, nullable=False)
	task_id = Column(Integer, ForeignKey('tasks.id'), primary_key=True, nullable=True)
