import cgi

from .auth import UserInfo
from .prerequisite import PrerequisitiesEvaluator
from .task import TaskStatus

from . import admin

from . import module
from . import task
from . import prerequisite
from . import quiz
from . import sortable
from . import programming
from . import achievement
from . import user
from . import profile
from . import thread
from . import post
from . import mail
from . import config
from . import text
from . import correction
from . import correctionInfo
from . import wave
from . import submissions
from . import year
from . import content
from . import git
from . import lock
from . import feedback


def decode_form_data(req):
    ctype, pdict = cgi.parse_header(req.content_type)
    return cgi.parse_multipart(req.stream, pdict)
