from db import session
import model, util

def to_json(wave, sum_points=None):
	if sum_points is None: sum_points = util.task.max_points_wave_dict()[wave.id]

	return {
		'id': wave.id,
		'year': wave.year,
		'index': wave.index,
		'caption': wave.caption,
		'garant': wave.garant,
		'time_published': wave.time_published.isoformat(),
		'public': wave.public,
		'sum_points': sum_points
	}

