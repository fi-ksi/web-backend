import datetime

from sqlalchemy import Column, Integer, ForeignKey, String, TIMESTAMP, text, Text
from . import Base
from .user import User
from .year import Year

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True)
    created = Column(TIMESTAMP, nullable=False,
                          default=datetime.datetime.utcnow,
                          server_default=text('CURRENT_TIMESTAMP'))
    user_id = Column(Integer,
                     ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=True)
    year_id = Column(Integer,
                     ForeignKey(Year.id, ondelete='CASCADE'),
                     nullable=True)
    scope = Column(String(50), nullable=True)
    line = Column(Text, nullable=False)
    line_meta = Column(Text, nullable=True)
