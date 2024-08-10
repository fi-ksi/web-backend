from sqlalchemy import Column, String

from . import Base


class Config(Base):
    __tablename__ = 'config'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    key = Column(String(100), primary_key=True, nullable=False)
    value = Column(String(200), nullable=True)
