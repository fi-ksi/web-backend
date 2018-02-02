from sqlalchemy import Column, Integer, ForeignKey

from . import Base
from .user import User
from .achievement import Achievement
from .task import Task


class UserAchievement(Base):
    __tablename__ = 'user_achievement'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     primary_key=True, nullable=False)
    achievement_id = Column(Integer,
                            ForeignKey(Achievement.id, ondelete='CASCADE'),
                            primary_key=True, nullable=False)
    task_id = Column(Integer, ForeignKey(Task.id, ondelete='CASCADE'),
                     nullable=True)
