import falcon
import json
import git
from lockfile import LockFile
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class TaskMerge(object):

    def on_post(self, req, resp, id):
        """
        Vraci JSON:
        {
            "result": "ok" | "error",
            "error": String
        }

        """

        try:
            user = req.context['user']

            # Kontrola existence ulohy
            task = session.query(model.Task).get(id)
            if task is None:
                req.context['result'] = 'Neexistujici uloha'
                resp.status = falcon.HTTP_404
                return

            # Kontrola existence git_branch a git_path
            if (task.git_path is None) or (task.git_branch is None):
                req.context['result'] = ('Uloha nema zadanou gitovskou vetev '
                                         'nebo adresar')
                resp.status = falcon.HTTP_400
                return

            if task.git_branch == "master":
                req.context['result'] = 'Uloha je jiz ve vetvi master'
                resp.status = falcon.HTTP_400
                return

            wave = session.query(model.Wave).get(task.wave)

            # Merge mohou provadet pouze administratori a garant vlny
            if (not user.is_logged_in()) or (not user.is_admin() and
                                             user.id != wave.garant):
                req.context['result'] = 'Nedostatecna opravneni'
                resp.status = falcon.HTTP_400
                return

            # Kontrola zamku
            lock = util.lock.git_locked()
            if lock:
                req.context['result'] = ('GIT uzamcen zámkem '+lock +
                                         '\nNekdo momentalne provadi akci s '
                                         'gitem, opakujte prosim akci za 20 '
                                         'sekund.')
                resp.status = falcon.HTTP_409
                return

            try:
                mergeLock = LockFile(util.admin.taskMerge.LOCKFILE)
                mergeLock.acquire(60)  # Timeout zamku je 1 minuta

                # Fetch repozitare
                repo = git.Repo(util.git.GIT_SEMINAR_PATH)

                if task.git_branch in repo.heads:
                    # Cannot delete branch we are on
                    repo.git.checkout("master")
                    repo.git.branch('-D', task.git_branch)

                task.git_branch = 'master'

                session.commit()
                resp.status = falcon.HTTP_200
                req.context['result'] = {}
            finally:
                mergeLock.release()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
