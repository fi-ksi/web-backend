from sqlalchemy import Column, Integer, SmallInteger, String, Text, Enum, Boolean, ForeignKey, text
from sqlalchemy.orm import relationship

from . import Base

class QuizQuestion(Base):
	__tablename__ = 'quiz_questions'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	module = Column(Integer, ForeignKey('modules.id'), nullable=False)
	type = Column(Enum('checkbox', 'radio'), default='checkbox', server_default='checkbox', nullable=False)
	question = Column(Text, nullable=False)
	order = Column(SmallInteger, nullable=False, default=1, server_default='1')

	options = relationship('QuizOption', primaryjoin='QuizQuestion.id==QuizOption.quiz')

class QuizOption(Base):
	__tablename__ = 'quiz_options'
	__table_args__ = {
		'mysql_engine': 'InnoDB',
		'mysql_charset': 'utf8',
	}

	id = Column(Integer, primary_key=True)
	quiz = Column(Integer, ForeignKey(QuizQuestion.id), nullable=False)
	value = Column(Text, nullable=False)
	is_correct = Column(Boolean, nullable=False, default=False, server_default=text('FALSE'))
	order = Column(SmallInteger, nullable=False, default=1, server_default='1')
