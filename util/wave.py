from db import session
import model
from util import config

def to_json(wave):
	return {
		'id': wave.id,
		'year': wave.year,
		'index': wave.index,
		'caption': wave.caption,
		'garant': wave.garant,
		'time_published': wave.time_published.isoformat(),
		'public': wave.public
	}

