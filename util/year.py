# -*- coding: utf-8 -*-

from db import session
import model
from util import config
import util

def to_json(year, sum_points=None):
	if sum_points is None: sum_points = util.task.max_points_year_dict()[year.id]
	print sum_points

	return {
		'id': year.id,
		'index': year.id,
		'year': year.year,
		'sum_points': sum_points[0],
		'tasks_cnt': int(sum_points[1]),
		'sealed': year.sealed,
		'point_pad': year.point_pad
	}

def year_end(year):
	return int(year.year.replace(" ", "").split("/")[0]) + 1
