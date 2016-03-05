# -*- coding: utf-8 -*-

from db import session
import model
from util import config

def to_json(year, sum_points=None):
	if sum_points is None: sum_points = util.task.max_points_year_dict()[year.id]

	return {
		'id': year.id,
		'index': year.id,
		'year': year.year,
		'sum_points': sum_points
	}

