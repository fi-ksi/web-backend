# -*- coding: utf-8 -*-

from db import session
import model
import util

def to_json(post, user_id, last_visit=None, last_visit_filled=False, reactions=None):
	if user_id:
		if not last_visit_filled:
			last_visit = session.query(model.ThreadVisit).get((thread_id. user_id))
		is_new = True if (last_visit is None) or (last_visit.last_last_visit is None) else last_visit.last_last_visit < post.published_at
	else:
		is_new = False

	if reactions is None: reactions = post.reactions

	return {
		'id': post.id,
		'thread': post.thread,
		'author': post.author,
		'body': post.body,
		'published_at': post.published_at.isoformat(),
		'reaction': [ reaction.id for reaction in reactions ],
		'is_new': is_new
	}

def to_html(post, author=None):
	if not author: author = session.query(model.User).get(post.author)
	return "<p><i><a href=\"%s\">%s</a></i>:</p>%s" % (util.config.ksi_web() + "/profil/" +str(author.id), author.first_name + " " + author.last_name, post.body)
