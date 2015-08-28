from db import session
import model


class Debug(object):
    def on_get(self, req, resp):
        user_normal = model.User()
        user_normal.admin = False
        user_normal.login = 'user'
        user_normal.password = '1234'

        session.add(user_normal)
        session.commit()

        print('Created user user:1234')
