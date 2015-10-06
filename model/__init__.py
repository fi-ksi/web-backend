from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from model.article import Article
from model.achievement import Achievement
from model.category import Category
from model.post import Post
from model.task import Task, SolutionComment
from model.prerequisite import Prerequisite, PrerequisiteType
from model.module import Module, ModuleType
from model.programming import Programming, CodeExecution
from model.quiz import QuizQuestion, QuizOption
from model.sortable import Sortable
from model.thread import Thread, ThreadVisit
from model.user import User
from model.profile import Profile
from model.evaluation import Evaluation
from model.token import Token
from model.submitted import SubmittedFile, SubmittedCode
from model.user_achievement import UserAchievement
