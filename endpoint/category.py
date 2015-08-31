from db import session
import model


class Category(object):
    def schema_generator(self, model_instances):
        inst = model_instances
        return {'category': {
            'id': inst.id, 'title': inst.title, 'color': inst.color
        }}

    def on_get(self, req, resp, id):
        category = session.query(model.Category).get(id)
        req.context['result'] = self.schema_generator(category)


class Categories(object):
    def schema_generator(self, model_instances):
        return {'categories': [
            {'id': inst.id, 'title': inst.title, 'color': inst.color}
            for inst in model_instances
        ]}

    def on_get(self, req, resp):
        categories = session.query(model.Category).all()
        req.context['result'] = self.schema_generator(categories)
