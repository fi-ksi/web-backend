from sqlalchemy import Column, Integer, String, Text, ForeignKey

from . import Base

class SubmittedFile(Base):
	__tablename__ = 'submitted_files'
	__table_args__ = (
		{
			'mysql_engine': 'InnoDB',
			'mysql_charset': 'utf8',
		})

	id = Column(Integer, primary_key=True)
	evaluation = Column(Integer, ForeignKey('evaluations.id'), nullable=False)
	mime = Column(String(255))
	path = Column(String(255), nullable=False)

class SubmittedCode(Base):
	__tablename__ = 'submitted_codes'
	__table_args__ = (
		{
			'mysql_engine': 'InnoDB',
			'mysql_charset': 'utf8',
		})

	evaluation = Column(Integer, ForeignKey('evaluations.id'), primary_key=True, nullable=False)
	code = Column(Text, nullable=False)
