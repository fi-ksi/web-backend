class Profile(object):
    def _schema(self, req):
        return {'profile': [
            {'id': 1, 'is_logged': bool(req.env['PERMISSIONS'])}
        ]}

    def on_get(self, req, resp):
        req.context['result'] = self._schema(req)
