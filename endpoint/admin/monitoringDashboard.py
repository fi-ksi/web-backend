import config
import falcon

class MonitoringDashboard(object):

    def on_get(self, req, resp):
        resp.media = {'url': config.MONITORING_DASHBOARD_URL}
        resp.status = falcon.HTTP_200

