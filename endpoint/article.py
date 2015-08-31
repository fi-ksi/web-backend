from db import session
import model


class Article(object):
    def _schema(self, model_instances):
        inst = model_instances
        return {'article':
                {'id': inst.id, 'title': inst.title, 'body': inst.body,
                 'time_published': inst.time_created, 'picture': None}
                }

    def on_get(self, req, resp, id):
        articles = session.query(model.Article).get(id)
        req.context['result'] = self._schema(articles)


class Articles(object):
    def _schema(self, model_instances):
        return {'articles': [
            {'id': inst.id, 'title': inst.title, 'body': inst.body,
             'time_published': inst.time_created, 'picture': None}
            for inst in model_instances
        ], 'meta': {'total': 2}}

    def on_get(self, req, resp):
        articles = session.query(model.Article).all()
        req.context['result'] = self._schema(articles)
