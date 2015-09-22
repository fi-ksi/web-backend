import auth


class Auth(object):
    provider = auth.Provider()

    def on_get(self, req, resp):
        self.provider.authorization_request(req, resp)


class Token(object):
    provider = auth.Provider()

    def on_get(self, req, resp):
        self.provider.access_token_request(req, resp)
