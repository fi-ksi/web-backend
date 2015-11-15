from db import session
import model

def to_json(thread, user_id=None):
	count = len(thread.posts)
	unread = count_unread(user_id, thread.id)

	return {
		'id': thread.id,
		'title': thread.title,
		'unread': unread if unread is not None else count,
		'posts_count': count,
		'details': thread.id
	}

def details_to_json(thread):
	root_posts = [ post.id for post in session.query(model.Post).filter(model.Post.thread == thread.id, model.Post.parent == None) ]

	return {
		'id': thread.id,
		'root_posts': root_posts
	}

def get_visit(user_id, thread_id):
	return session.query(model.ThreadVisit).filter(model.ThreadVisit.user == user_id, model.ThreadVisit.thread == thread_id).first()

def count_unread(user_id, thread_id):
	if user_id is None:
		return 0

	visit = get_visit(user_id, thread_id)

	if not visit:
		return None

	return session.query(model.Post).filter(model.Post.thread == thread_id, model.Post.published_at > visit.last_visit).count()

