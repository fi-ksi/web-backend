# -*- coding: utf-8 -*-

from model import PrerequisiteType

# Prerekvizity uloh maji omezeni:
# OR nemuze byt vnitrni po AND
# (13 && 12) || (15 && 16) validni
# (13 || 12) || (15 && 16) validni
# (13 || 12) && (15 && 16) NEvalidni

class orList(list):
    def __init__(self, *args, **kwargs):
        super(orList, self).__init__(args[0])

class andList(list):
    def __init__(self, *args, **kwargs):
        super(andList, self).__init__(args[0])

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
            return andList([ self._parse_expression(child) for child in prereq.children ])

        if(prereq.type == PrerequisiteType.OR):
            return orList([ self._parse_expression(child) for child in prereq.children ])

    def _evaluation_step(self, expr):
        if expr is None:
            return True

        if type(expr) is andList:
            val = True
            for item in expr:
                val = val and self._evaluation_step(item)
            return val

        if type(expr) is orList:
            val = False
            for item in expr:
                val = val or self._evaluation_step(item)
            return val

        return expr in self.fully_submitted
