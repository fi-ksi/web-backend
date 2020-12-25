import falcon


class Robots(object):

    def on_get(self, req, resp):
        resp.content_type = 'text/plain'
        resp.body = "User-agent: *\nDisallow: /"
