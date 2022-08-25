import datetime

from sqlalchemy import Column, Integer, ForeignKey, Boolean
from . import Base
from .user import User
from .year import Year


class Diploma(Base):
    __tablename__ = 'diplomas'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     primary_key=True)
    year_id = Column(Integer, ForeignKey(Year.id, ondelete='CASCADE'),
                     primary_key=True)
    revoked = Column(Boolean, nullable=False, default=False)
