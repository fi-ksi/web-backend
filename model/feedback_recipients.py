from sqlalchemy import Column, Integer, String

from . import Base

class FeedbackRecipient(Base):
    __tablename__ = 'feedback_recipients'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8'
    }

    email = Column(String(200), primary_key=True)

