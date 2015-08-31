from db import session
import model


class User(object):
    def _schema(self, model_instances):
        inst = model_instances

        return {'user':
                {'id': inst.id, 'first_name': inst.name_first,
                 'last_name': inst.name_last}
                }

    def on_get(self, req, resp, id):
        user = session.query(model.User).get(id)
        req.context['result'] = self._schema(user)


class Users(object):
    def _schema(self, model_instances):
        return {'users': [
            {'id': inst.id, 'first_name': inst.name_first,
             'last_name': inst.name_last} for inst in model_instances
        ]}

    def on_get(self, req, resp):
        users = session.query(model.User).all()
        req.context['result'] = self._schema(users)
