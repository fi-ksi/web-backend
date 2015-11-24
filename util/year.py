from db import session
import model
from util import config

def to_json(year):
	return {
		'id': year.id,
		'year': year.year
	}

