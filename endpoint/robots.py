import falcon


class Robots(object):

    def on_get(self, req, resp):
        resp.body = "User-agent: *\nDisallow: /"
