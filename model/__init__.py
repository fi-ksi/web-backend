from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from model.year import Year
from model.wave import Wave
from model.config import Config
from model.profile import Profile
from model.user import User
from model.article import Article
from model.achievement import Achievement
from model.thread import Thread, ThreadVisit
from model.post import Post
from model.prerequisite import Prerequisite, PrerequisiteType
from model.task import Task, SolutionComment
from model.module import Module, ModuleType
from model.module_custom import ModuleCustom
from model.token import Token
from model.user_achievement import UserAchievement
from model.mail_easteregg import MailEasterEgg
from model.feedback_recipients import FeedbackRecipient
from model.programming import CodeExecution
from model.evaluation import Evaluation
from model.submitted import SubmittedFile, SubmittedCode
from model.active_orgs import ActiveOrg
from model.feedback import Feedback
from model.user_notify import UserNotify
from model.diploma import Diploma

