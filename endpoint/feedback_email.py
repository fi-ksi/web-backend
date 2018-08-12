import json

import util


class FeedbackEmail(object):

    def on_post(self, req, resp):
        data = json.loads(req.stream.read().decode('utf-8'))

        if len(data['body']) == 0:
            return

        if 'email' not in data:
            data['email'] = "ksi@fi.muni.cz"

        util.mail.send_feedback(data['body'].encode('utf-8'), data['email'])

        req.context['result'] = {'result': 'ok'}
