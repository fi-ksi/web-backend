import falcon
from io import StringIO
from sqlalchemy import func, distinct, desc, text
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class UserExport(object):

    def _stringify_users(self, users, sum_points):
        """
        Pomocna metoda pro zapis uzivatelu do souboru
        Vraci string k zapisu do souboru

        """

        res = ""
        order = 0
        last_points = -1
        for i in range(0, len(users)):
            user, profile, points, tasks_cnt, cheat = users[i]

            if points != last_points:
                order = i + 1
                last_points = points

            res += \
                str(order) + ";" +\
                user.last_name + ";" +\
                user.first_name + ";" +\
                str(points) + ";" +\
                ('A' if points >= 0.6 * sum_points and not cheat else 'N') + ";" +\
                ('A' if cheat else 'N') + ";" +\
                user.email + ";" +\
                user.sex + ";" +\
                profile.addr_street + ";" +\
                profile.addr_city + ";" +\
                profile.addr_zip + ";" +\
                profile.addr_country + ";" +\
                profile.school_name + ";" +\
                profile.school_street + ";" +\
                profile.school_city + ";" +\
                profile.school_zip + ";" +\
                profile.school_country + ";" +\
                str(profile.school_finish) + ";" +\
                profile.tshirt_size + '\n'

        return res

    def on_get(self, req, resp):
        """ Vraci csv vsech resitelu vybraneho rocniku. """

        try:
            user = req.context['user']
            year_obj = session.query(model.Year).get(req.context['year'])

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            inMemoryOutputFile = StringIO()

            # Tady se dela spoustu magie kvuli tomu, aby se usetrily SQL dotazy
            # Snazime se minimalizovat pocet dotazu, ktere musi byt provedeny
            # pro kadeho uzivatele
            # a misto toho provest pouze jeden MEGA dotaz.

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
            # i napriklad automaticky opravovane moduly s 0 body).
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
            # Tem, kteri maji evaluations, je prirazen pocet bodu a pocet
            # odevzdanych uloh.
            # Vraci n tici: (model.User, total_score, tasks_cnt, model.Profile)
            users = session.query(
                model.User,
                model.Profile,
                func.sum(per_user.c.points).label("total_score"),
                tasks_per_user.c.tasks_cnt.label('tasks_cnt'),
                func.max(per_user.c.cheat).label('cheat'),
            ).\
                join(per_user, model.User.id == per_user.c.user).\
                join(tasks_per_user, model.User.id == tasks_per_user.c.user).\
                join(model.Profile, model.User.id == model.Profile.user_id).\
                filter(model.User.role == 'participant').\
                filter(text("tasks_cnt"), text("tasks_cnt > 0")).\
                group_by(model.User).\
                order_by(desc("total_score"),
                         model.User.last_name, model.User.first_name)

            year_end = util.year.year_end(year_obj)
            users_hs = users.filter(model.Profile.school_finish >= year_end).\
                all()
            users_other = users.filter(model.Profile.school_finish <
                                       year_end).\
                all()

            sum_points = util.task.sum_points(
                req.context['year'],
                bonus=False) + year_obj.point_pad
            sum_points_bonus = util.task.sum_points(
                req.context['year'],
                bonus=True) + year_obj.point_pad

            table_header = \
                "Pořadí;" +\
                "Příjmení;" +\
                "Jméno;" +\
                "Body;" +\
                "Úspěšný řešitel;" +\
                "Podvod;" +\
                "E-mail;" +\
                "Pohlaví;" +\
                "Ulice;" +\
                "Město;" +\
                "PSČ;" +\
                "Země;" +\
                "Škola;" +\
                "Adresa školy;" +\
                "Město školy;" +\
                "PSČ školy;" +\
                "Země školy;" +\
                "Rok maturity;" +\
                "Velikost trička\n"

            inMemoryOutputFile.write(
                "Celkem bodů: " + str(sum_points) +
                ", včetně bonusových úloh: " + str(sum_points_bonus) +
                ", bodová vycpávka: " + str(year_obj.point_pad) + '\n'
            )

            # Resitele stredoskolaci
            inMemoryOutputFile.write("Středoškoláci\n")
            inMemoryOutputFile.write(table_header)
            inMemoryOutputFile.write(self._stringify_users(users_hs,
                                                           sum_points))

            # Resitele ostatni
            inMemoryOutputFile.write("\nOstatní\n")
            inMemoryOutputFile.write(table_header)
            inMemoryOutputFile.write(self._stringify_users(users_other,
                                                           sum_points))

            resp.set_header(
                'Content-Disposition',
                ('inline; filename="resitele_' + str(req.context['year']) +
                 '.csv"')
            )
            resp.content_type = "text/csv"
            resp.body = inMemoryOutputFile.getvalue()
            resp.stream_len = len(resp.body)

            inMemoryOutputFile.close()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
