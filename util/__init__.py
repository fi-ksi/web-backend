import cgi

def decode_form_data(req):
	ctype, pdict = cgi.parse_header(req.content_type)
	return cgi.parse_multipart(req.stream, pdict)

class PrerequisitiesEvaluator:

	def __init__(self, task_valuation, root_prerequisite):
		self.task_valuation = task_valuation
		self.root_prerequisite = root_prerequisite

	def evaluate(self):
		expr = self._parse_expression(self.root_prerequisite)
		return self._evaluation_step(expr)

	def _parse_expression(self, prereq):
		if(prereq.type == 'ATOMIC'):
			return prereq.task

		if(prereq.type == 'AND'):
			return [ self._parse_expression(child) for child in prereq.children ]

		if(prereq.type == 'OR'):
			return { self._parse_expression(child) for child in prereq.children }

	def _evaluation_step(self, expr):
		if type(expr) is list:
			val = True
			for item in expr:
				val = val and self._evaluation_step(item)
			return val

		if type(expr) is set:
			val = False
			for item in expr:
				val = val or self._evaluation_step(item)
			return val

		return self.task_valuation[expr]


class UserInfo:

	def __init__(self, user=None, token=None):
		self.id = user.id if user else None
		self.role = user.role if user else None
		self.token = token

	def is_logged_in(self):
		return self.id is not None

	def get_id(self):
		return self.id

	def is_admin(self):
		return self.role == 'admin'
