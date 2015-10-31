from sqlalchemy import Column, String

from . import Base

class MailEasterEgg(Base):
	__tablename__ = 'mail_easteregg'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8'
	}

	id = Column(String(100), primary_key=True, nullable=False)
	body = Column(String(200), nullable=False)