# -*- coding: utf-8 -*-

import falcon

class Robots(object):

    def on_get(self, req, resp):
        resp.body = "User-agent: *\nDisallow: /"

