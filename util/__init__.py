import cgi

from auth import UserInfo
from prerequisite import PrerequisitiesEvaluator
from task import TaskStatus

import module
import task
import prerequisite
import quiz
import sortable
import programming
import achievement
import user
import profile
import thread
import post
import mail
import config
import text

def decode_form_data(req):
	ctype, pdict = cgi.parse_header(req.content_type)
	return cgi.parse_multipart(req.stream, pdict)
