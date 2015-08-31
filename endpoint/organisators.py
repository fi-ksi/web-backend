from db import session
import model


class Organisator(object):
    def _schema(self, model_instances):
        inst = model_instances
        return {'organisator':
                {'id': inst.id, 'first_name': inst.name_first,
                 'last_name': inst.name_last}
                }

    def on_get(self, req, resp, id):
        organisator = session.query(model.User).get(id)
        req.context['result'] = self._schema(organisator)


class Organisators(object):
    def _schema(self, model_instances):
        return {'organisators': [
            {'id': inst.id, 'first_name': inst.name_first,
             'last_name': inst.name_last} for inst in model_instances
        ]}

    def on_get(self, req, resp):
        organisators = session.query(model.User).all()
        req.context['result'] = self._schema(organisators)
