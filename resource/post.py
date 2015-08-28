from db import session
import model


class Post(object):
    def schema_generator(self, model_instances):
        inst = model_instances
        return {'post':
                {'id': inst.id, 'title': inst.title, 'body': inst.body,
                 'time_published': inst.time_created}
                }

    def on_get(self, req, resp, id):
        post = session.query(model.Post).get(id)
        req.context['result'] = self.schema_generator(post)


class Posts(object):
    def schema_generator(self, model_instances):
        return {'posts': [
            {'id': inst.id, 'title': inst.title, 'body': inst.body,
             'time_published': inst.time_created} for inst in model_instances
        ]}

    def on_get(self, req, resp):
        posts = session.query(model.Post).all()
        req.context['result'] = self.schema_generator(posts)
