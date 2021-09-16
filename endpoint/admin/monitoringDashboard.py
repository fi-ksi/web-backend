import falcon

class MonitoringDashboard(object):

    def on_get(self, req, resp):
        resp.media = {'message': 'https://test1.example'}
        resp.status = falcon.HTTP_200

