import datetime

from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

from . import Base
from .user import User


class Profile(Base):
    __tablename__ = 'profiles'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     primary_key=True)
    addr_street = Column(String(255), nullable=False)
    addr_city = Column(String(255), nullable=False)
    addr_zip = Column(String(20), nullable=False)
    addr_country = Column(String(255), nullable=False)
    school_name = Column(String(255), nullable=False)
    school_street = Column(String(255), nullable=False)
    school_city = Column(String(255), nullable=False)
    school_zip = Column(String(20), nullable=False)
    school_country = Column(String(255), nullable=False)
    school_finish = Column(Integer, nullable=False)
    tshirt_size = Column(Enum('XS', 'S', 'M', 'L', 'XL', 'NA'), nullable=False)
    referral = Column(String(4096), nullable=True)
