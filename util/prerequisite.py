from model import PrerequisiteType
from db import session

# Prerekvizity uloh maji omezeni:
# OR nemuze byt vnitrni po AND
# (13 && 12) || (15 && 16) validni
# (13 || 12) || (15 && 16) validni
# (13 || 12) && (15 && 16) NEvalidni

def to_json(prereq):
	if(prereq.type == PrerequisiteType.ATOMIC):
		return [ [ prereq.task ] ]

	if(prereq.type == PrerequisiteType.AND):
		return [ _to_json2(prereq) ]

	if(prereq.type == PrerequisiteType.OR):
		return _to_json2(prereq)

def _to_json2(prereq):
	if(prereq.type == PrerequisiteType.ATOMIC):
		return [ prereq.task ]

	elif(prereq.type == PrerequisiteType.AND):
		l = []
		for child in prereq.children: l.extend(_to_json2(child))
		return l

	elif(prereq.type == PrerequisiteType.OR):
		# Propagujeme ORy nahoru
		l = []
		for child in prereq.children:
			l_in = _to_json2(child)
			if isinstance(l_in[0], list):
				l.extend(l_in)
			else:
				l.append(l_in)
		return l

	else:
		return []

# Smaze vsechny deti \root, \root zachova pri delete_root
# Po zavolani funkce je nutne volat session.commit()
def remove_tree(root, delete_root=False, my_session=session):
	if root is None: return
	for child in root.children: remove_tree(child, True, my_session)
	if delete_root:
		try:
			my_session.delete(root)
		except:
			my_session.rollback()
			raise

class PrerequisitiesEvaluator:

	def __init__(self, root_prerequisite, fully_submitted):
		self.root_prerequisite = root_prerequisite
		self.fully_submitted = fully_submitted

	def evaluate(self):
		expr = self._parse_expression(self.root_prerequisite)
		return self._evaluation_step(expr)

	def _parse_expression(self, prereq):
		if prereq is None:
			return None

		if(prereq.type == PrerequisiteType.ATOMIC):
			return prereq.task

		if(prereq.type == PrerequisiteType.AND):
			return [ self._parse_expression(child) for child in prereq.children ]

		if(prereq.type == PrerequisiteType.OR):
			return [ self._parse_expression(child) for child in prereq.children ]

	def _evaluation_step(self, expr):
		if expr is None:
			return True

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

		return expr in self.fully_submitted
