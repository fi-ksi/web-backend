import falcon
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from db import session
from model import CodeExecution as CE
import util


class Exec(object):
    """ This endpoint returns single code execution. """

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            execution = sessiton.query(CE).get(id)

            if not execution:
                resp.status = falcon.HTTP_404
                return

            req.context['result'] = util.programming.exec_to_json(execution)

        except SQLAlchemyError:
            session.rollback()
            raise

        finally:
            session.close()


class Execs(object):
    """ This endpoint returns code executions. """

    def on_get(self, req, resp):
        """
        You can send request with any of these GET parameters:
        ?user=user_id
        ?module=module_id
        ?limit=uint, (default=20)
        ?page=uint,
        ?from=datetime,
        ?to=datetime,
        ?result=(ok,error),

        Most recent evaluatons are returned first.
        """

        try:
            user = req.context['user']

            if (not user.is_logged_in() or not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            execs = session.query(CE)

            ruser = req.get_param_as_int('user')
            if ruser is not None:
                execs = execs.filter(CE.user == ruser)

            rmodule = req.get_param_as_int('module')
            if rmodule is not None:
                execs = execs.filter(CE.module == rmodule)

            rfrom = req.get_param_as_datetime('from', '%Y-%m-%d %H:%M:%S')
            if rfrom is not None:
                execs = execs.filter(CE.time >= rfrom)

            rto = req.get_param_as_datetime('to', '%Y-%m-%d %H:%M:%S')
            if rto is not None:
                execs = execs.filter(CE.time <= rto)

            rresult = req.get_param('result')
            if rresult is not None:
                execs = execs.filter(CE.result == rresult)

            limit = req.get_param_as_int('limit')
            if limit is None or limit < 1:
                limit = 20
            if limit > 100:
                limit = 100

            page = req.get_param_as_int('page')
            if page is None or page < 0:
                page = 0

            count = execs.count()

            execs = execs.order_by(desc(CE.id)).\
                slice(limit*page, limit*(page+1))
            execs = execs.all()

            req.context['result'] = {
                'execs': [util.programming.exec_to_json(ex) for ex in execs],
                'meta': {
                    'total': count,
                    'page': page,
                },
            }

        except SQLAlchemyError:
            session.rollback()
            raise

        finally:
            session.close()
