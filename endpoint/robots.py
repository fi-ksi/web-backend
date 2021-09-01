import falcon


class Robots(object):
    def on_head(self, req, resp):
        self.on_get(req=req, resp=resp)
        resp.body = ''

    def on_get(self, req, resp):
        resp.content_type = 'text/plain'
        resp.body = "User-agent: *\nDisallow: /"
