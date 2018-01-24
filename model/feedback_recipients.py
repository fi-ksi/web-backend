from sqlalchemy import Column, Integer, String

from . import Base


class FeedbackRecipient(Base):
    __tablename__ = 'feedback_recipients'
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }

    email = Column(String(150), primary_key=True)
