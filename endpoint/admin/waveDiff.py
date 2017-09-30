import falcon
import git
import os
from sqlalchemy.exc import SQLAlchemyError
from lockfile import LockFile

from db import session
import model
import util


class WaveDiff(object):

    def on_post(self, req, resp, id):
        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            # Kontrola zamku
            lock = util.lock.git_locked()
            if lock:
                req.context['result'] = ('GIT uzamcen zamkem ' + lock +
                                         '\nNekdo momentalne provadi akci s '
                                         'gitem, opakujte prosim akci za 20 '
                                         'sekund.')
                resp.status = falcon.HTTP_409
                return

            pullLock = LockFile(util.admin.waveDiff.LOCKFILE)
            pullLock.acquire(60)  # Timeout zamku je 1 minuta

            # Fetch
            repo = git.Repo(util.git.GIT_SEMINAR_PATH)
            repo.remotes.origin.fetch()

            # Ulohy ve vlne
            tasks = session.query(model.Task).\
                filter(model.Task.wave == id).all()

            # Diffujeme adresare uloh task.git_commit oproti HEAD
            for task in tasks:
                if ((not task.git_branch) or (not task.git_path) or
                        (not task.git_commit)):
                    task.deploy_status = 'default'
                    continue

                # Checkout && pull vetve ve ktere je uloha
                repo.git.checkout(task.git_branch)
                repo.remotes.origin.pull()

                # Kontrola existence adresare ulohy
                if os.path.isdir(util.git.GIT_SEMINAR_PATH + task.git_path):
                    hcommit = repo.head.commit
                    diff = hcommit.diff(task.git_commit, paths=[task.git_path])
                    if len(diff) > 0:
                        task.deploy_status = 'diff'
                else:
                    task.deploy_status = 'default'

            session.commit()
            req.context['result'] = {}
        except SQLAlchemyError:
            session.rollback()
            req.context['result'] = 'Nastala vyjimka backendu'
            raise
        finally:
            pullLock.release()
            session.close()
