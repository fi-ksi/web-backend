import datetime

from sqlalchemy import Column, Integer, String, Boolean, DECIMAL

from . import Base


class Year(Base):
    __tablename__ = 'years'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    id = Column(Integer, primary_key=True, nullable=False)
    year = Column(String(100), nullable=True)
    sealed = Column(Boolean, nullable=False, default=False)
    point_pad = Column(DECIMAL(precision=10, scale=1, asdecimal=False),
                       nullable=False, default=0)
