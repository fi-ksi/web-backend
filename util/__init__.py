import cgi

from auth import UserInfo
from prerequisite import PrerequisitiesEvaluator

import module
import task
import prerequisite
import quiz
import sortable
import programming
import achievement
import user
import score
import profile
import thread

def decode_form_data(req):
	ctype, pdict = cgi.parse_header(req.content_type)
	return cgi.parse_multipart(req.stream, pdict)
