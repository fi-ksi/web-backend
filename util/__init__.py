import cgi

from auth import UserInfo
from prerequisite import PrerequisitiesEvaluator

def decode_form_data(req):
	ctype, pdict = cgi.parse_header(req.content_type)
	return cgi.parse_multipart(req.stream, pdict)
