import falcon
import json
import sys
import traceback

import util

# Content-security policy reports of frontend
# Every CSP report is forwarded to ksi-admin@fi.muni.cz.
# This is testing solution, if a lot of spam occurs, some intelligence should
# be added to this endpoint.


class CSP(object):

    def on_post(self, req, resp):
        data = json.loads(req.stream.read().decode('utf-8'))

        # Ignore "about" violations caused by Disconnect plugin
        if "csp-report" not in data:
            req.context['result'] = {}
            resp.status = falcon.HTTP_200
            return

        if "blokced-uri" in data["csp-report"] and \
           data["csp-report"]["blocked-uri"] == "about":
            req.context['result'] = {}
            resp.status = falcon.HTTP_200
            return

        text = "<p>" + util.config.ksi_web() + \
            "<br><pre>" + json.dumps(data, indent=4, ensure_ascii=False) + "</pre></p>" + \
            util.mail.easteregg()

        try:
            #util.mail.send("me@apophis.cz", "[Naskoc na FI] CSP report", text, )
            pass
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      file=sys.stderr)

        req.context['result'] = {}
        resp.status = falcon.HTTP_200
