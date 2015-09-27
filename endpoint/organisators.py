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
        #organisator = session.query(model.User).get(id)
        req.context['result'] = {'organisator': {
      "id": 1,
      "first_name": "Honza",
      "last_name": "Mrazek",
      "nick_name": "",
      "profile_picture": "http://placehold.it/50x50"
    } }


class Organisators(object):
    def _schema(self, model_instances):
        return {'organisators': [
            {'id': inst.id, 'first_name': inst.name_first,
             'last_name': inst.name_last} for inst in model_instances
        ]}

    def on_get(self, req, resp):
        #organisators = session.query(model.User).all()
        #req.context['result'] = self._schema(organisators)

        req.context['result'] = { "organisators": [
    {
      "id": 1,
      "first_name": "Honza",
      "last_name": "Mrazek",
      "nick_name": "",
      "profile_picture": "http://placehold.it/50x50"
    },
    {
      "id": 2,
      "first_name": "Henrich",
      "last_name": "Lauko",
      "nick_name": "Heno",
      "profile_picture": "http://placehold.it/50x50"
    }
  ]}
