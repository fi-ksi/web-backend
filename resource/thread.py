from db import session
import model


class Thread(object):
    def schema_generator(self, model_instances):
        inst = model_instances
        return {'thread': {
            'id': inst.id, 'title': inst.title
        }}

    def on_get(self, req, resp, id):
        threads = session.query(model.Thread).get(id)
        req.context['result'] = self.schema_generator(threads)


class Threads(object):
    def schema_generator(self, model_instances):
        return {'threads': [
            {'id': inst.id, 'title': inst.title}
            for inst in model_instances
        ]}

    def on_get(self, req, resp):
        threads = session.query(model.Thread).all()
        req.context['result'] = self.schema_generator(threads)
