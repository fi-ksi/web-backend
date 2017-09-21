from sqlalchemy import Column, Integer, ForeignKey

from . import Base
from .user import User
from .year import Year


class ActiveOrg(Base):
    __tablename__ = 'active_orgs'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    org = Column(Integer,
                 ForeignKey(User.id, ondelete='CASCADE'),
                 primary_key=True,
                 nullable=False)

    year = Column(Integer,
                  ForeignKey(Year.id, ondelete='CASCADE'),
                  primary_key=True,
                  nullable=False)
