import falcon
import json
import datetime
from sqlalchemy.exc import SQLAlchemyError
from lockfile import LockFile

from db import session
import model
import util


class Task(object):

    def on_get(self, req, resp, id):
        try:
            user = req.context['user']
            fetch_testers = req.get_param_as_bool('fetch_testers')
            task = session.query(model.Task).get(id)

            # task_admin mohou ziskat jen orgove
            if (not user.is_logged_in()) or (not user.is_org()):
                req.context['result'] = {
                    'errors': [{
                        'status': '401',
                        'title': 'Unauthorized',
                        'detail': 'Přístup odepřen.'
                    }]
                }
                resp.status = falcon.HTTP_400
                return

            if task is None:
                req.context['result'] = {
                    'errors': [{
                        'status': '404',
                        'title': 'Not Found',
                        'detail': 'Úloha s tímto ID neexistuje.'
                    }]
                }
                resp.status = falcon.HTTP_404
                return

            req.context['result'] = {'atask': util.admin.task.admin_to_json(task, do_fetch_testers=fetch_testers)}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_put(self, req, resp, id):
        """ UPDATE ulohy """

        try:
            user = req.context['user']
            data = json.loads(req.stream.read().decode('utf-8'))['atask']
            wave = session.query(model.Wave).get(data['wave'])

            if wave is None:
                resp.status = falcon.HTTP_404
                return

            if (not user.is_logged_in()) or (not user.is_admin() and
                                             user.id != wave.garant):
                resp.status = falcon.HTTP_400
                return

            task = session.query(model.Task).get(id)
            if task is None:
                resp.status = falcon.HTTP_404
                return

            # Ulohu lze editovat jen pred casem zverejneni vlny
            wave = session.query(model.Wave).get(task.wave)
            if (datetime.datetime.utcnow() > wave.time_published and
                    not user.is_admin()):
                resp.status = falcon.HTTP_403
                return

            task.title = data['title']
            task.git_path = data['git_path']
            task.git_branch = data['git_branch']
            task.git_commit = data['git_commit']
            if 'eval_comment' in data:
                if data['eval_comment'] == '':
                    data['eval_comment'] = None
                task.eval_comment = data['eval_comment']

            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

        self.on_get(req, resp, id)

    def on_delete(self, req, resp, id):
        """ Smazani ulohy """

        try:
            user = req.context['user']

            # Ulohu mohou smazat jen admini
            if (not user.is_logged_in()) or (not user.is_admin()):
                resp.status = falcon.HTTP_400
                return

            task = session.query(model.Task).get(id)
            if task is None:
                resp.status = falcon.HTTP_404
                return

            # Ulohu lze smazat jen pred casem zverejneni vlny
            wave = session.query(model.Wave).get(task.wave)
            if datetime.datetime.utcnow() > wave.time_published:
                resp.status = falcon.HTTP_403
                return

            execs = session.query(model.CodeExecution).\
                join(
                    model.Module,
                    model.Module.id == model.CodeExecution.module
                ).\
                filter(model.Module.task == id).all()
            for _exec in execs:
                session.delete(_exec)

            evals = session.query(model.Evaluation).\
                join(model.Module, model.Module.id == model.Evaluation.module).\
                filter(model.Module.task == id).all()
            for _eval in evals:
                session.delete(_eval)

            session.query(model.Module).\
                filter(model.Module.task == id).delete()

            thread = session.query(model.Thread).get(task.thread)
            prer = task.prerequisite_obj
            if prer is not None:
                session.delete(task.prerequisite_obj)

            session.delete(task)
            session.commit()

            if thread is not None:
                session.delete(thread)

            session.commit()

            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()


class Tasks(object):

    def on_get(self, req, resp):
        try:
            user = req.context['user']
            wave = req.get_param_as_int('wave')

            # Zobrazovat task_admin mohou jen orgove
            if (not user.is_logged_in()) or (not user.is_org()):
                req.context['result'] = {
                    'errors': [{
                        'status': '401',
                        'title': 'Unauthorized',
                        'detail': 'Přístup odepřen.'
                    }]
                }
                resp.status = falcon.HTTP_400
                return

            tasks = session.query(model.Task, model.Wave).\
                join(model.Wave, model.Task.wave == model.Wave.id)

            if wave is None:
                tasks = tasks.filter(model.Wave.year == req.context['year'])
            else:
                tasks = tasks.filter(model.Wave.id == wave)
            tasks = tasks.all()

            max_points = util.task.max_points_dict()

            req.context['result'] = {
                'atasks': [
                    util.admin.task.admin_to_json(task.Task,
                                            max_points[task.Task.id])
                    for task in tasks
                ]
            }
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def on_post(self, req, resp):
        """
        Vytvoreni nove ulohy

        Specifikace POST pozadavku:
        {
            "task": {
                "wave": Integer, <- id vlny
                "title": String,
                "author": Integer, <- id autora
                "git_path": String, <- adresar ulohy v GITu vcetne cele cesty
                "git_branch": String, <- nazev gitove vetve, ve ktere vytvorit
                    ulohu / ze ktere cerpat data pro deploy
                "git_commit" String <- hash posledniho commitu, pokud je
                    ?create_git=true, nevyplnuje se
                "git_create" Bool <- jestli ma dojit k vytvoreni gitovskeho
                    adresare a vetve ulohy
            }
        }

        """

        try:
            user = req.context['user']
            year = req.context['year']
            data = json.loads(req.stream.read().decode('utf-8'))['atask']
            wave = session.query(model.Wave).get(data['wave'])

            if wave is None:
                resp.status = falcon.HTTP_404
                return

            # Vytvorit novou ulohu mohou jen admini nebo garanti vlny.
            if (not user.is_logged_in()) or (not user.is_admin() and
                                             user.id != wave.garant):
                resp.status = falcon.HTTP_401
                return

            # Ulohu lze vytvorit jen pred casem zverejneni vlny
            if datetime.datetime.utcnow() > wave.time_published:
                resp.status = falcon.HTTP_403
                req.context['result'] = {'errors': 'Po zverejneni vlny nelze vytvaret nove ulohy'}
                return

            github_pull_id = None

            # Vytvoreni adresare v repu je option:
            if ('git_create' in data) and (data['git_create']):
                # Kontrola zamku
                lock = util.lock.git_locked()
                if lock:
                    resp.status = falcon.HTTP_409
                    return

                newLock = LockFile(util.admin.task.LOCKFILE)
                newLock.acquire(60)  # Timeout zamku je 1 minuta

                try:
                    git_commit, github_pull_id = util.admin.task.createGit(
                        data['git_path'], data['git_branch'],
                        int(data['author']), data['title'])
                finally:
                    newLock.release()
            else:
                git_commit = data['git_commit']\
                    if 'git_commit' in data else None

            # Nejprve vytvorime nove diskuzni vlakno
            taskThread = model.Thread(
                title=data['title'],
                public=True,
                year=req.context['year']
            )
            session.add(taskThread)
            session.commit()

            # Pote vytvorime ulohu
            task = model.Task(
                wave=data['wave'],
                title=data['title'],
                author=data['author'],
                git_path=data['git_path'],
                git_branch=data['git_branch'],
                git_commit=git_commit,
                git_pull_id=github_pull_id,
                thread=taskThread.id
            )

            session.add(task)
            session.commit()

            req.context['result'] = {'atask': util.admin.task.admin_to_json(task)}
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
