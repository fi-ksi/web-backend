class Profile(object):
    def schema_generator(self):
        return {'profile': [{'id': 1}]}

    def on_get(self, req, resp):
        req.context['result'] = self.schema_generator()
