import model
from db import session


class Diploma:
    def on_get(self, req, resp, id):
        diplomas = session.query(model.Diploma)\
            .filter(model.Diploma.user_id == id)

        req.context['result'] = {
            'diplomas': [{
                'year': diploma.year_id,
                'revoked': diploma.revoked
            } for diploma in diplomas]
        }
