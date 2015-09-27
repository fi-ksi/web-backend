from db import session
import model

def _category_to_json(category):
	return { 'id': category.id, 'type': category.type, 'color': 'red'}

class Category(object):
	def schema_generator(self, model_instances):
		inst = model_instances
		return {'category': {
			'id': inst.id, 'title': inst.title, 'color': inst.color
		}}

	def on_get(self, req, resp, id):
		category = session.query(model.Category).get(id)

		req.context['result'] = { 'category': _category_to_json(category) }


class Categories(object):

	def on_get(self, req, resp):
		categories = session.query(model.Category).all()
		req.context['result'] = { 'categories': [ _category_to_json(category) for category in categories ] }
