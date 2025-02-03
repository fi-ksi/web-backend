import sys
import falcon
import json
import random
import string
from sqlalchemy import func, distinct, desc, text, or_, select
from sqlalchemy.exc import SQLAlchemyError
import traceback

from db import session
import model
import model.user
import util
import auth
from util import config, cache
from util.logger import audit_log


class User(object):

    def on_get(self, req, resp, id):
        try:
            user = session.query(model.User).get(id)
        except SQLAlchemyError:
            session.rollback()
            raise

        if user is None:
            req.context['result'] = {
                'errors': [{
                    'status': '404',
                    'title': 'Not found',
                    'detail': 'Uživatel s tímto ID neexistuje.'
                }]
            }
            resp.status = falcon.HTTP_404
            return

        try:
            req.context['result'] = {
                'user': util.user.to_json(
                    user,
                    req.context['year_obj'],
                    admin_data=req.context['user'].is_org()
                )
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_delete(self, req, resp, id):
        user = req.context['user']
        try:
            user_db = session.query(model.User).get(id)
        except SQLAlchemyError:
            session.rollback()
            raise

        if (not user.is_logged_in()) or (not user.is_admin()):
            resp.status = falcon.HTTP_400
            return

        if not user_db:
            resp.status = falcon.HTTP_404
            return

        profile = session.query(model.Profile).get(id)

        try:
            if profile:
                session.delete(profile)
            session.delete(user_db)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        req.context['result'] = {}


class DiscordInviteLink(object):

    def on_get(self, req, resp, id):
        userinfo = req.context['user']

        if not userinfo.is_logged_in():
            resp.status = falcon.HTTP_401
            return

        if not userinfo.user.discord:
            req.context['result'] = None
            return

        req.context['result'] = config.discord_invite_link()


class DiscordBotValidateUser(object):
    
    def on_post(self, req, resp):
        data = json.loads(req.stream.read().decode('utf-8'))
        api_key = config.discord_bot_secret()
        
        if "Secret" not in data or "Username" not in data:
            resp.status = falcon.HTTP_400
            return
        
        if not api_key or data["Secret"] != api_key:
            resp.status = falcon.HTTP_403
            return
        
        username = data["Username"]
        statement = select(model.User).where(model.User.discord == username)
        linked_profile = session.execute(statement).one_or_none()
        
        if linked_profile is None:
            resp.status = falcon.HTTP_404
            return
        
        req.context['result'] = {
            "first_name": linked_profile[0].first_name,
            "last_name": linked_profile[0].last_name,
            "nick_name": linked_profile[0].nick_name,
        }
        
        


class Users(object):

    def on_get(self, req, resp):
        filt = req.get_param('filter')
        sort = req.get_param('sort')
        usr = req.context['user']
        year = req.context['year_obj']

        cache_key = cache.get_key(None, 'org' if usr.is_org() else 'participant', req.context['year'], f'users_score:{filt=}:{sort=}')
        cached_data = cache.get_record(cache_key)
        if cached_data is not None:
            req.context['result'] = cached_data
            return

        """
        Tady se dela spoustu magie kvuli tomu, aby se usetrily SQL dotazy
        Snazime se minimalizovat pocet dotazu, ktere musi byt provedeny pro
        kazdeho uzivatele
        a misto toho provest pouze jeden MEGA dotaz.
        Slouzi predevsim pro rychle nacitani vysledkove listiny.
        """

        try:
            # Skore uzivatele per modul (zahrnuje jen moduly evaluation_public)
            per_user = session.query(
                model.Evaluation.user.label('user'),
                func.max(model.Evaluation.points).label('points'),
                func.max(model.Evaluation.cheat).label('cheat'),
            ).\
                join(model.Module,
                     model.Evaluation.module == model.Module.id).\
                join(model.Task, model.Task.id == model.Module.task).\
                filter(model.Task.evaluation_public).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Wave.year == req.context['year']).\
                group_by(model.Evaluation.user, model.Evaluation.module).\
                subquery()

            # Pocet odevzdanych uloh (zahrnuje i module not evaluation_public
            # i napriklad automaticky opravovane moduly s 0 body)
            tasks_per_user = session.query(
                model.Evaluation.user.label('user'),
                func.count(distinct(model.Task.id)).label('tasks_cnt')
            ).\
                join(model.Module,
                     model.Evaluation.module == model.Module.id).\
                join(model.Task, model.Task.id == model.Module.task).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Wave.year == req.context['year']).\
                group_by(model.Evaluation.user).subquery()

            # Ziskame vsechny uzivatele
            # Tem, kteri maji evaluations, je prirazen pocet bodu a
            # pocet odevzdanych uloh
            # Vraci n tici:
            # (model.User, total_score, tasks_cnt, model.Profile, cheat)
            # POZOR: outerjoin je dulezity, chceme vracet i uzivatele,
            # kteri nemaji zadna evaluations (napriklad orgove pro seznam orgu)
            users = session.query(
                model.User,
                func.sum(per_user.c.points).label("total_score"),
                tasks_per_user.c.tasks_cnt.label('tasks_cnt'),
                model.Profile,
                func.max(per_user.c.cheat).label('cheat'),
            ).\
                outerjoin(per_user, model.User.id == per_user.c.user).\
                outerjoin(tasks_per_user,
                          model.User.id == tasks_per_user.c.user).\
                join(model.Profile, model.User.id == model.Profile.user_id).\
                group_by(model.User)

            # Filtrovani skupin uzivatelu
            if filt == 'organisators' or filt == 'orgs':
                users = users.filter(or_(model.User.role == 'org',
                                         model.User.role == 'admin')).\
                    join(model.ActiveOrg,
                         model.ActiveOrg.org == model.User.id).\
                    filter(model.ActiveOrg.year == year.id)

            elif filt == 'orgs-all':
                users = users.filter(or_(model.User.role == 'org',
                                         model.User.role == 'admin'))

            elif filt == 'part-hs':
                # Resitele zobrazujeme jen v aktualnim rocniku
                # (pro jine neni tasks_cnt definovano).
                users = users.filter(model.User.role == 'participant').\
                    having(text("total_score > 0"))
                if year:
                    users = users.filter(model.Profile.school_finish >=
                                         util.year.year_end(year))

            elif filt == 'part-other':
                users = users.filter(model.User.role == 'participant').\
                    having(text("total_score > 0"))
                if year:
                    users = users.filter(model.Profile.school_finish <
                                         util.year.year_end(year))

            elif filt == 'part' or filt == 'participants':
                users = users.filter(model.User.role == 'participant').\
                    filter(text("tasks_cnt"), text("tasks_cnt > 0"))
            # Razeni uzivatelu
            if sort == 'score':
                users = users.order_by(desc("total_score"))

            # Polozime SQL dotaz a ziskame vsechny relevantni uzivatele
            users = users.all()

            # A ted prijdou na radu hratky a achievementy a aktivnimi rocniky:
            # seznamy patrici kazdemu uzivateli
            # Samozrejme nechceme pro kazdeho uzivatele delat zvlastni dotaz.

            # Achievementy:
            achievements = session.query(model.User.id.label('user_id'),
                                         model.Achievement.id.label('a_id')).\
                join(model.UserAchievement,
                     model.UserAchievement.user_id == model.User.id).\
                join(model.Achievement,
                     model.Achievement.id ==
                     model.UserAchievement.achievement_id).\
                filter(or_(model.Achievement.year == year.id,
                           model.Achievement.year == None)).\
                group_by(model.User.id, model.Achievement.id).\
                all()

            # Aktivni roky:
            seasons = session.query(model.Year.id.label('year_id'),
                                    model.User.id.label('user_id')).\
                join(model.Wave, model.Wave.year == model.Year.id).\
                join(model.Task, model.Task.wave == model.Wave.id).\
                join(model.Module, model.Module.task == model.Task.id).\
                join(model.Evaluation,
                     model.Evaluation.module == model.Module.id).\
                join(model.User, model.Evaluation.user == model.User.id).\
                group_by(model.User.id, model.Year.id).\
                all()

            # Aktivni roky orgu:
            org_seasons = session.query(model.Year.id.label('year_id'),
                                        model.User.id.label('user_id')).\
                join(model.ActiveOrg, model.ActiveOrg.year == model.Year.id).\
                join(model.User, model.User.id == model.ActiveOrg.org).\
                all()

            # Ziskani seznamu uloh vsech orgu na jeden dotaz
            users_tasks = session.query(model.User, model.Task).\
                join(model.Task, model.User.id == model.Task.author).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Wave.year == year.id).\
                group_by(model.User, model.Task).all()

            users_co_tasks = session.query(model.User, model.Task).\
                join(model.Task, model.User.id == model.Task.co_author).\
                join(model.Wave, model.Wave.id == model.Task.wave).\
                filter(model.Wave.year == year.id).\
                group_by(model.User, model.Task).all()

            max_points = max(
                util.task.sum_points(req.context['year'], bonus=False),
                year.point_pad
            )

            # Uzivatele s nedefinovanymi tasks_cnt v tomto rocniku
            # neodevzdali zadnou ulohu
            # -> nastavime jim natvrdo 'tasks_cnt' = 0 a total_score = 0,
            # abychom omezili dalsi SQL dotazy v util.user.to_json

            users_json = [
                util.user.to_json(
                    user=user.User,
                    year_obj=year,
                    total_score=user.total_score if user.total_score else 0,
                    tasks_cnt=user.tasks_cnt if user.tasks_cnt else 0,
                    profile=user.Profile,
                    achs=[item.a_id for item in achievements
                          if item.user_id == user.User.id],
                    seasons=[item.year_id for item in seasons
                             if item.user_id == user.User.id],
                    users_tasks=[
                        task for (_, task) in [
                            usr_task
                            for usr_task in users_tasks
                            if usr_task[0].id == user.User.id
                        ]
                    ] if users_tasks else None,
                    admin_data=usr.is_org(),
                    org_seasons=[
                        item.year_id
                        for item in org_seasons if item.user_id == user.User.id
                    ],
                    max_points=max_points,
                    users_co_tasks=[
                        task for (_, task) in [
                            usr_task1
                            for usr_task1 in users_co_tasks
                            if usr_task1[0].id == user.User.id
                        ]
                    ]
                    if users_co_tasks else None,
                    cheat=user.cheat,
                )

                for user in users
            ]
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        req.context['result'] = {
            'users': users_json
        }
        cache.save_cache(cache_key, req.context['result'], 30 * 60)


class ChangePassword(object):

    def on_post(self, req, resp):
        user = req.context['user']

        if not user.is_logged_in():
            resp.status = falcon.HTTP_400
            return

        try:
            user = session.query(model.User).get(user.id)
        except SQLAlchemyError:
            session.rollback()
            raise

        data = json.loads(req.stream.read().decode('utf-8'))

        if not auth.check_password(data['old_password'], user.password):
            resp.status = falcon.HTTP_401
            req.context['result'] = {'result': 'error'}
            return

        if data['new_password'] != data['new_password2']:
            req.context['result'] = {'result': 'error'}
            return

        user.password = auth.get_hashed_password(data['new_password'])

        try:
            session.add(user)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        req.context['result'] = {'result': 'ok'}


class ForgottenPassword(object):

    def on_post(self, req, resp):
        email = json.loads(req.stream.read().decode('utf-8'))['email']
        try:
            user = session.query(model.User).\
                filter(model.User.email == email).\
                first()
        except SQLAlchemyError:
            session.rollback()
            raise

        if not user:
            resp.status = falcon.HTTP_400
            req.context['result'] = {'result': 'error'}
            return

        new_password = ''.join(
            random.SystemRandom().
            choice(string.ascii_uppercase + string.digits +
                   string.ascii_lowercase)
            for _ in range(16))

        audit_log(
            scope="AUTH",
            user_id=user.id,
            message=f"Password reset",
            message_meta={
                'role': user.role,
                'ip': req.context['source_ip']
            }
        )
        user.password = auth.get_hashed_password(new_password)

        try:
            session.add(user)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

        try:
            util.mail.send(
                user.email,
                f'{util.config.mail_subject_prefix()} Nové heslo',
                'Ahoj,<br/>na základě tvé žádosti ti bylo vygenerováno nové '
                f'heslo: {new_password}<br/><br/>{util.config.seminar_name()}'
            )
        except SQLAlchemyError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      file=sys.stderr)

        session.close()

        req.context['result'] = {'result': 'ok'}
