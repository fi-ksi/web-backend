from db import session
import model


class Task(object):
    def _schema(self, model_instances):
        inst = model_instances

        return {'task':
                {'id': inst.id, 'position': [inst.position_x, inst.position_y],
                 'category': inst.id_category, 'title': inst.title,
                 'body': inst.body, 'max_score': inst.max_score,
                 'time_deadline': inst.time_deadline,
                 'time_published': inst.time_published}
                }

    def on_get(self, req, resp, id):
        tasks = session.query(model.Task).get(id)
        req.context['result'] = self._schema(tasks)


class Tasks(object):
    def _schema(self, model_instances):
        return {'tasks': [
            {'id': inst.id, 'position': [inst.position_x, inst.position_y],
             'category': inst.id_category, 'title': inst.title,
             'body': inst.body, 'max_score': inst.max_score,
             'time_deadline': inst.time_deadline,
             'time_published': inst.time_published} for inst in model_instances
        ]}

    def on_get(self, req, resp):
        tasks = session.query(model.Task).all()
        req.context['result'] = self._schema(tasks)
