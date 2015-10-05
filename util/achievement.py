from db import session
import model

def to_json(achievement, user_id):
	show_picture = user_id and session.query(model.UserAchievement).filter(model.UserAchievement.achievement_id == achievement.id, model.UserAchievement.user_id == user_id).first() is not None

	return { 'id': achievement.id, 'title': achievement.title, 'active': True, 'picture': '/img/achievements/' + (achievement.code if show_picture else 'achievement-unknown') + '.svg' }

def ids_set(achievements):
	return set([ achievement.id for achievement in achievements ])

def ids_list(achievements):
	return list(ids_set(achievements))
