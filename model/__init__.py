from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from model.article import Article
from model.achievement import Achievement
from model.category import Category
from model.post import Post
from model.task import Task
from model.prerequisite import Prerequisite
from model.module import Module
from model.programming import Programming
from model.quiz import QuizQuestion, QuizOption
from model.sortable import Sortable
from model.thread import Thread
from model.user import User
from model.profile import Profile
from model.submission import Submission
from model.evaluation import Evaluation

#~ from model.auth import Token
