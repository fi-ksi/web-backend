# -*- coding: utf-8 -*-

import falcon
import json
from sqlalchemy import and_, text, not_, desc, func, distinct, or_
from sqlalchemy.orm import load_only
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util

class Thread(object):

    def on_put(self, req, resp, id):
        try:
            user_id = req.context['user'].id if req.context['user'].is_logged_in() else None

            if not user_id:
                return

            if session.query(model.Thread).get(id) is None:
                status = falcon.HTTP_400
                return

            visit = util.thread.get_visit(user_id, id)

            if visit:
                visit.last_last_visit = visit.last_visit
                visit.last_visit = text('CURRENT_TIMESTAMP')
            else:
                visit = model.ThreadVisit(thread=id, user=user_id, last_visit=text('CURRENT_TIMESTAMP'))
                session.add(visit)

            session.commit()
            req.context['result'] = "{}"
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']
            user_id = req.context['user'].id if req.context['user'].is_logged_in() else None
            thread = session.query(model.Thread).get(id)

            if not thread:
                req.context['result'] = { 'errors': [ { 'status': '404', 'title': 'Not Found', 'detail': u'Toto vlákno neexistuje.' } ] }
                resp.status = falcon.HTTP_404
                return

            if (not thread) or (not thread.public and not (user.is_org() or util.thread.is_eval_thread(user.id, thread.id))):
                req.context['result'] = { 'errors': [ { 'status': '401', 'title': 'Unauthorized', 'detail': u'Přístup k vláknu odepřen.' } ] }
                resp.status = falcon.HTTP_400
                return

            # Pocet vsech prispevku
            posts_cnt = session.query(model.Post).filter(model.Post.thread == thread.id).count()
            # Pocet neprectenych prispevku
            if not user.is_logged_in():
                unread_cnt = posts_cnt
            else:
                visit = session.query(model.ThreadVisit).filter(model.ThreadVisit.user == user.id, model.ThreadVisit.thread == thread.id).first()
                if visit:
                    unread_cnt = session.query(model.Post).filter(model.Post.thread == thread.id, model.Post.published_at > visit.last_visit).count()
                else:
                    unread_cnt = posts_cnt

            req.context['result'] = { 'thread': util.thread.to_json(thread, user_id, unread_cnt, posts_cnt) }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class Threads(object):

    def on_post(self, req, resp):
        try:
            user = req.context['user']
            if not user.is_logged_in():
                resp.status = falcon.HTTP_400
                return

            if req.context['year_obj'].sealed:
                resp.status = falcon.HTTP_403
                req.context['result'] = { 'errors': [ { 'status': '403', 'title': 'Forbidden', 'detail': u'Ročník zapečetěn.' } ] }
                return

            data = json.loads(req.stream.read())
            pblic = data['thread']['public'] if data['thread'].has_key('public') else True

            if len(data['thread']['title']) > 100:
                resp.status = falcon.HTTP_413
                req.context['result'] = { 'errors': [ { 'status': '413', 'title': 'Payload too large', 'detail': u'Název vlákna mít maximálně 100 znaků.' } ] }
                return

            thread = model.Thread(title=data['thread']['title'], public=pblic, year = req.context['year'])
            session.add(thread)
            session.commit()

            req.context['result'] = { 'thread': util.thread.to_json(thread, user.id) }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    """
        Parametry: ?wave=integer filtruje vlakna k urcite vlne
    """
    def on_get(self, req, resp):
        try:
            user_id = req.context['user'].id if req.context['user'].is_logged_in() else None
            show_all = (not (user_id is None)) and (req.context['user'].role == 'admin' or req.context['user'].role == 'org')

            wave = req.get_param_as_int('wave')

            # Pocet vsech prispevku
            posts_cnt = session.query(model.Thread.id.label('thread'), func.count(model.Post).label('posts_cnt')).\
                join(model.Post, model.Post.thread == model.Thread.id).\
                group_by(model.Thread.id).subquery()

            # Pocet neprectenych prispevku
            unread = session.query(model.Thread.id.label('thread'), model.ThreadVisit.thread.label('thread_visit'), func.count(model.Post.id).label('unread_cnt')).\
                outerjoin(model.ThreadVisit, and_(model.ThreadVisit.thread == model.Thread.id, model.ThreadVisit.user == user_id)).\
                outerjoin(model.Post, and_(model.Post.thread == model.Thread.id, model.Post.published_at > model.ThreadVisit.last_visit)).\
                group_by(model.Thread.id).subquery()

            threads = session.query(model.Thread, model.Task, posts_cnt.c.posts_cnt.label('posts_cnt'), unread.c.unread_cnt.label('unread_cnt'), unread.c.thread_visit.label('thread_visit')).\
                outerjoin(model.Task, model.Task.thread == model.Thread.id).\
                outerjoin(posts_cnt, posts_cnt.c.thread == model.Thread.id).\
                outerjoin(unread, unread.c.thread == model.Thread.id).\
                filter(model.Thread.public, model.Thread.year == req.context['year'])
            if wave: threads = threads.filter(model.Task.wave == wave)
            threads = threads.order_by(desc(model.Thread.id)).all()

            if not wave: threads = filter(lambda (thr,tsk,p,u,tv): tsk == None, threads)

            thr_output = []
            for (thread, _, posts_cnt, unread_cnt, thread_visit) in threads:
                if not posts_cnt: posts_cnt = 0
                if user_id and thread_visit:
                    uunread_cnt = unread_cnt if unread_cnt else 0
                else:
                    uunread_cnt = posts_cnt
                thr_output.append(util.thread.to_json(thread, user_id, uunread_cnt, posts_cnt))

            req.context['result'] = { 'threads': thr_output }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class ThreadDetails(object):

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']
            thread = session.query(model.Thread).get(id)

            if (not thread) or (not thread.public and not (user.is_org() or util.thread.is_eval_thread(user.id, thread.id))):
                resp.status = falcon.HTTP_400
                return

            last_visit = util.thread.get_visit(user.id, thread.id)
            posts = session.query(model.Post).filter(model.Post.thread == thread.id).all()

            req.context['result'] = {
                'threadDetails': util.thread.details_to_json(thread),
                'posts': [ util.post.to_json(post, user.id, last_visit, last_visit_filled=True, \
                    reactions=filter(lambda pst: pst.parent == post.id, posts)) for post in posts ]
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

