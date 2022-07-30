import falcon

from util import config

class MonitoringDashboard(object):

    def on_get(self, req, resp):
        user = req.context['user']
        
        if (not user.is_logged_in()) or (not user.is_org()):
            req.context['result'] = 'Nedostatecna opravneni'
            resp.status = falcon.HTTP_400
            return

        resp.media = {'url': config.monitoring_dashboard_url()}
        resp.status = falcon.HTTP_200

