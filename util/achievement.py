
def to_json(achievement):
	return { 'id': achievement.id, 'title': achievement.title, 'active': True, 'picture_active': 'img/achievements/' + achievement.code + '.svg' }

def ids_set(achievements):
	return set([ achievement.id for achievement in achievements ])

def ids_list(achievements):
	return list(ids_set(achievements))
