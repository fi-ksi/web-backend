from db import session
import model


class Achievement(object):
    def schema_generator(self, model_instances):
        inst = model_instances
        return {'achievements': {
            'id': inst.id, 'title': inst.title
        }}

    def on_get(self, req, resp, id):
        achievements = session.query(model.Achievement).get(id)
        req.context['result'] = self.schema_generator(achievements)


class Achievements(object):
    def schema_generator(self, model_instances):
        return {'achievements': [
            {'id': inst.id, 'title': inst.title} for inst in model_instances
        ]}

    def on_get(self, req, resp):
        achievements = session.query(model.Achievement).all()
        req.context['result'] = self.schema_generator(achievements)
