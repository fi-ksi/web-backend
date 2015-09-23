import auth


class Authorize(object):
    provider = auth.Provider()

    def on_post(self, req, resp):
        self.provider.request_access_token(req, resp)


class Refresh(object):
    provider = auth.Provider()

    def on_get(self, req, resp):
        self.provider.refresh_access_token(req, resp)
