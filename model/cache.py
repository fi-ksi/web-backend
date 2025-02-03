from sqlalchemy import Column, String, Text, TIMESTAMP

from . import Base


class Cache(Base):
    __tablename__ = 'cache'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    key = Column(String(220), primary_key=True, nullable=False)
    value = Column(Text(), nullable=False)
    expires = Column(TIMESTAMP, nullable=False)
