import falcon
import json
import re
from sqlalchemy import func, and_, or_, not_
from sqlalchemy.exc import SQLAlchemyError
import datetime

from db import session
import model
import util


class Correction(object):

    def on_get(self, req, resp, id):
        """
        GET pozadavek na konkretni correction se spousti prevazne jako odpoved
        na POST.
        id je umele id, konstrukce viz util/correction.py
        Parametry: moduleX_version=Y (X a Y jsou cisla)

        """

        try:
            user = req.context['user']
            year = req.context['year']
            task = int(id) / 100000
            participant = int(id) % 100000

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            # Ziskame prislusna 'evaluation's
            corrs = session.query(model.Evaluation, model.Task, model.Module).\
                filter(model.Evaluation.user == participant).\
                join(model.Module,
                     model.Module.id == model.Evaluation.module).\
                join(model.Task, model.Task.id == model.Module.task).\
                join(model.Wave, model.Task.wave == model.Wave.id).\
                join(model.Year, model.Year.id == model.Wave.year).\
                filter(model.Year.id == year).\
                filter(model.Task.id == task)

            task_id = corrs.group_by(model.Task).first()
            if task_id is None:
                resp.status = falcon.HTTP_404
                return

            task_id = task_id.Task.id
            corr_evals = corrs.group_by(model.Evaluation).all()
            corr_modules = corrs.group_by(model.Module).all()

            # Parsovani GET pozadavku:
            specific_evals = {}
            for param in req.params:
                module = re.findall(r'\d+', param)
                if module:
                    specific_evals[int(module[0])] =\
                        session.query(model.Evaluation).\
                        get(req.get_param_as_int(param))

            req.context['result'] = {
                'correction': util.correction.to_json(
                    [
                        (corr, mod, specific_evals[mod.id]
                         if mod.id in specific_evals else None)
                        for (corr, task, mod) in corr_modules
                    ],
                    [evl for (evl, tsk, mod) in corr_evals],
                    task_id)
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def _process_thread(self, corr):
        """ PUT: propojeni diskuzniho vlakna komentare """

        curr_thread = util.task.comment_thread(corr['task_id'], corr['user'])

        if (corr['comment'] is not None) and (curr_thread is None):
            # pridavame diskuzni vlakno
            try:
                comment = model.SolutionComment(
                    thread=corr['comment'],
                    user=corr['user'],
                    task=corr['task_id']
                )
                session.add(comment)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

        if (corr['comment'] is None) and (curr_thread is not None):
            # mazeme diskuzni vlakno
            try:
                comment = session.query(model.SolutionComment).\
                    get((curr_thread, corr['user'], corr['task_id']))
                session.delete(comment)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise

    def _process_achievements(self, corr):
        """ PUT: pridavani a mazani achievementu """

        a_old = util.achievement.ids_list(
            util.achievement.per_task(corr['user'], corr['task_id'])
        )
        a_new = corr['achievements']
        if a_old != a_new:
            # achievementy se nerovnaji -> proste smazeme vsechny dosavadni
            # a pridame do db ty, ktere nam prisly.
            for a_id in a_old:
                try:
                    ach = session.query(model.UserAchievement).\
                        get((corr['user'], a_id))
                    if ach.task_id == corr['task_id']:
                        session.delete(ach)
                    session.commit()
                except SQLAlchemyError:
                    session.rollback()
                    raise

            for a_id in a_new:
                try:
                    ua = model.UserAchievement(
                        user_id=corr['user'],
                        achievement_id=a_id,
                        task_id=corr['task_id']
                    )
                    session.add(ua)
                    session.commit()
                except SQLAlchemyError:
                    session.rollback()
                    raise
                finally:
                    session.close()

    def _process_evaluation(self, data_eval, user_id):
        """ PUT: zpracovani hodnoceni """

        try:
            evaluation = session.query(model.Evaluation).\
                get(data_eval['eval_id'])
            if evaluation is None:
                return

            evaluation.points = data_eval['points']
            evaluation.time = datetime.datetime.utcnow()
            evaluation.evaluator =\
                data_eval['corrected_by']\
                if 'corrected_by' in data_eval else user_id
            evaluation.full_report += (
                str(datetime.datetime.now()) + " : edited by org " +
                str(user_id) + " : " + str(data_eval['points']) +
                " points" + '\n'
            )
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

    def _process_module(self, data_module, user_id):
        """ PUT: zpracovani hodnoceni modulu """

        self._process_evaluation(data_module['evaluation'], user_id)

    def on_put(self, req, resp, id):
        """ PUT ma stejne argumenty, jako GET """

        user = req.context['user']

        if (not user.is_logged_in()) or (not user.is_org()):
            resp.status = falcon.HTTP_400
            return

        corr = json.loads(req.stream.read().decode('utf-8'))['correction']

        self._process_thread(corr)
        self._process_achievements(corr)

        for module in corr['modules']:
            self._process_module(module, user.id)

        # odpovedi jsou updatnute udaje
        self.on_get(req, resp, id)


class Corrections(object):
    """
    Tento endpoint je svou podstatou velmi sileny,
    protoze spojuje dohromady Tasks, Modules, Threads, Posts, Achievements,
    ... a my se snazime vsechny tyto vysledky
    vratit v konstatnim case. To vede k pomerne silenym hackum, viz nize.
    Cil: minimalizovat pocet SQL dotazu, provest jeden velky dotaz a vysledky
    pak filtrovat pythonim filter().

    """

    def on_get(self, req, resp):
        """
        Specifikace GET pozadavku:
        musi byt vyplnen alespon jeden z argumentu:
        ?task=task_id
        ?participant=user_id
        ?state=notcorrected|corrected

        """

        try:
            # Ziskama GET parametry
            user = req.context['user']
            year = req.context['year']
            task = req.get_param_as_int('task')
            participant = req.get_param_as_int('participant')
            state = req.get_param('state')

            # Vysledek vracime jen v pripade, kdy je vyplneno alespon jedlo z
            # 'task' nebo 'participant'
            if task is None and participant is None:
                resp.status = falcon.HTTP_400
                return

            # Login
            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            # Ziskame prislusna 'evaluation's v podobe seznamu [eval_id],
            # toto je subquery pro dalsi pozadavky.
            evals = session.query(model.Evaluation.id.label('eval_id'))
            if participant is not None:
                evals = evals.filter(model.Evaluation.user == participant)
            evals = evals.join(model.Module,
                               model.Module.id == model.Evaluation.module).\
                join(model.Task, model.Task.id == model.Module.task).\
                join(model.Wave, model.Task.wave == model.Wave.id).\
                join(model.Year, model.Year.id == model.Wave.year).\
                filter(model.Year.id == year)
            if task is not None:
                evals = evals.filter(model.Task.id == task)
            evals = evals.subquery()

            # Terminilogie:
            # "Opraveni" je Evaluation.group_by(Task, User).
            # Jedno opraveni muze mit mit vic modulu a evaluations, ma vzy ale
            # prave jednoho uzivatele a prave jednu ulohu.

            # Pomocny vypocet toho, jestli je dane hodnoceni opravene /
            # neopravene.
            # Tato query bere task_id a user_id a pokud je opraveni opravene,
            # vrati v is_corrected True
            corrected = session.query(
                model.Task.id.label('task_id'),
                model.User.id.label('user_id'),
                (func.count(model.Evaluation.id) > 0).label('is_corrected')
            ).\
                join(model.Module, model.Module.task == model.Task.id).\
                join(model.Evaluation,
                     model.Evaluation.module == model.Module.id).\
                join(model.User, model.Evaluation.user == model.User.id).\
                filter(or_(model.Module.autocorrect == True,
                           model.Evaluation.evaluator != None)).\
                group_by(model.Task.id, model.User.id).\
                subquery()

            # Ziskame corrections. Corrections = evalustions obohacena o dalsi
            # pole, jako je napriklad uloha, modul, ci diskuzni vlakno reseni
            # Tady se bohuzel trochu duplikuje predchozi kod, ale neumim to
            # vyresit lepe...
            corrs = session.query(
                model.Evaluation,
                model.Task,
                model.Module,
                model.Thread,
                corrected.c.is_corrected.label('is_corrected')
            ).\
                join(evals, model.Evaluation.id == evals.c.eval_id).\
                join(model.Module,
                     model.Evaluation.module == model.Module.id).\
                join(model.Task, model.Task.id == model.Module.task)

            # filtr opravenych uloh
            if state == 'corrected':
                corrs = corrs.join(
                    corrected,
                    and_(model.Task.id == corrected.c.task_id,
                         model.Evaluation.user == corrected.c.user_id)
                )
            else:
                corrs = corrs.outerjoin(
                    corrected,
                    and_(model.Task.id == corrected.c.task_id,
                         model.Evaluation.user == corrected.c.user_id)
                )

            if state == 'notcorrected':
                corrs = corrs.filter(or_(corrected.c.is_corrected == None,
                                         not_(corrected.c.is_corrected)))

            corrs = corrs.outerjoin(
                model.SolutionComment,
                and_(model.SolutionComment.user == model.Evaluation.user,
                     model.SolutionComment.task == model.Task.id)).\
                outerjoin(model.Thread,
                          model.SolutionComment.thread == model.Thread.id)

            # Evaluations si pogrupime podle uloh, podle toho vedeme result a
            # pak pomocne podle modulu (to vyuzivame pri budovani vystupu) a
            # jeste podle evaluations.
            corrs_tasks = corrs.\
                group_by(model.Task, model.Evaluation.user).\
                all()

            corrs_modules = corrs.\
                group_by(model.Module, model.Evaluation.user).\
                all()

            corrs_evals = corrs.\
                group_by(model.Evaluation, model.Evaluation.user).\
                all()

            # Achievementy po ulohach a uzivatelich:
            corrs_achs = session.query(
                model.Task.id,
                model.UserAchievement.user_id.label('user_id'),
                model.Achievement.id.label('a_id')
            )

            if task is not None:
                corrs_achs = corrs_achs.filter(model.Task.id == task)
            if participant is not None:
                corrs_achs = corrs_achs.\
                    filter(model.UserAchievement.user_id == participant)

            corrs_achs = corrs_achs.join(
                model.UserAchievement,
                model.UserAchievement.task_id == model.Task.id
            ).\
                join(model.Achievement,
                     model.Achievement.id ==
                     model.UserAchievement.achievement_id).\
                group_by(model.Task,
                         model.UserAchievement.user_id, model.Achievement).\
                all()

            # Vsechny achievementy pro hlavni seznam
            achievements = session.query(model.Achievement).\
                filter(model.Achievement.year == req.context['year']).all()

            # Pripravime si vsechny relevantni soubory k opravovanim na jeden
            # pozadavek.
            files = session.query(model.SubmittedFile).\
                join(evals,
                     model.SubmittedFile.evaluation == evals.c.eval_id).\
                all()

            # Prispevky ve vsech relevantnich diskuzich
            db_posts = session.query(model.Post, model.Thread).\
                join(model.Thread, model.Post.thread == model.Thread.id).\
                join(model.SolutionComment,
                     model.SolutionComment.thread == model.Thread.id).\
                join(model.Module,
                     model.Module.task == model.SolutionComment.task).\
                join(
                    model.Evaluation,
                    and_(model.Evaluation.module == model.Module.id,
                         model.SolutionComment.user == model.Evaluation.user)
                ).\
                join(evals, evals.c.eval_id == model.Evaluation.id)

            # Korenove prispevky vlaken
            root_posts = db_posts.filter(model.Post.parent == None).\
                group_by(model.Thread, model.Post).all()
            db_posts = db_posts.group_by(model.Post).all()

            # Budujeme vystup 'corrections'
            # Argumenty (a jejich format) funkce util.correction.to_json
            # popsany v ~/util/correction.py (toto je pomerne magicka funkce)
            corrections = []
            threads = []
            thr_details = []
            for corr in corrs_tasks:
                evals = [
                    x for x in corrs_evals
                    if (x.Task.id == corr.Task.id and
                        x.Evaluation.user == corr.Evaluation.user)
                ]

                corrections.append(util.correction.to_json(
                    [
                        (evl, mod, None)
                        for (evl, tsk, mod, thr, iscor) in [
                            x for x in corrs_modules
                            if (x.Task.id == corr.Task.id and
                                x.Evaluation.user == corr.Evaluation.user)
                        ]
                    ],
                    [evl for (evl, tsk, mod, thr, iscor) in evals],
                    evals[0].Task.id,
                    corr.Thread.id if corr.Thread else None,
                    [
                        r
                        for (a, b, r) in [
                            task_id_user_id_a_id
                            for task_id_user_id_a_id in corrs_achs
                            if (task_id_user_id_a_id[0] == corr.Task.id and
                                task_id_user_id_a_id[1] ==
                                corr.Evaluation.user)
                        ]
                    ],
                    (corr.is_corrected
                        if corr.is_corrected is not None else False),
                    files
                ))

                if corr.Thread:
                    threads.append(util.thread.to_json(corr.Thread, user.id))
                    r_posts = [
                        pst.id
                        for (pst, thrd) in [
                            post_thr
                            for post_thr in root_posts
                            if post_thr[1].id == corr.Thread.id
                        ]
                    ]

                    thr_details.append(
                        util.thread.details_to_json(corr.Thread, r_posts)
                    )

            # Ziskavame last_visit jednotlivych vlaken (opet na jeden SQL
            # pozadavek).
            last_visit = util.thread.get_user_visit(user.id, year)
            posts = []
            for (post, thread) in db_posts:
                lastv = None
                for lv in last_visit:
                    if lv.thread == post.thread:
                        lastv = lv
                        break
                posts.append(util.post.to_json(post, user.id, lastv, True))

            # A konecne vratime vysledek.
            req.context['result'] = {
                'corrections': corrections,
                'tasks': [
                    util.correction.task_to_json(q.Task)
                    for q in corrs.group_by(model.Task).all()
                ],
                'modules': [
                    util.correction.module_to_json(q.Module)
                    for q in corrs.group_by(model.Module).all()
                ],
                'achievements': [
                    util.achievement.to_json(achievement)
                    for achievement in achievements
                ],
                'threads': threads,
                'posts': posts,
                'threadDetails': thr_details
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
