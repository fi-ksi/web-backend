from sqlalchemy import Column, Integer, Text

from . import Base


class MailEasterEgg(Base):
    __tablename__ = 'mail_eastereggs'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    id = Column(Integer, primary_key=True, nullable=False)
    body = Column(Text, nullable=False)
