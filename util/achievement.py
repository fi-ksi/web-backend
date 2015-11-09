from db import session
import model
from util import config

def to_json(achievement, user_id):
	return { 'id': achievement.id, 'title': achievement.title, 'active': True, 'picture': '/content/achievements/' + achievement.code + '.svg', 'description': achievement.description }

def ids_set(achievements):
	return set([ achievement.id for achievement in achievements ])

def ids_list(achievements):
	return list(ids_set(achievements))
