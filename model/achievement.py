from sqlalchemy import Column, Integer, String, ForeignKey

from . import Base
from .year import Year


class Achievement(Base):
    __tablename__ = 'achievements'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    picture = Column(String(128), nullable=False, unique=False)
    description = Column(String(200), nullable=True)
    year = Column(Integer, ForeignKey(Year.id), nullable=True)
