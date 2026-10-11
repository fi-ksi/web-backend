import falcon
from sqlalchemy.exc import SQLAlchemyError
from io import BytesIO
from zipfile import ZipFile
import os

from db import session
import model
import util
from util.logger import get_log

class SubmFilesTask(object):

    def on_get(self, req, resp, task_id):
        """ Vraci vsechny soubory vsech resitelu pro danou ulohu. """

        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            inMemoryOutputFile = BytesIO()
            zipFile = ZipFile(inMemoryOutputFile, 'w')

            modules = session.query(model.Module).\
                filter(model.Module.task == task_id).all()

            for module in modules:
                users = session.query(model.User).\
                    join(model.Evaluation,
                         model.Evaluation.user == model.User.id).\
                    filter(model.Evaluation.module == module.id).all()

                for user in users:
                    evaluations = session.query(model.Evaluation.id).\
                        filter(model.Evaluation.user == user.id,
                               model.Evaluation.module == module.id).all()
                    evaluation_ids = [e for (e, ) in evaluations]

                    files = [
                        r for (r, ) in
                        session.query(model.SubmittedFile.path).
                        join(model.Evaluation,
                             model.Evaluation.id ==
                             model.SubmittedFile.evaluation).
                        filter(model.Evaluation.user == user.id,
                               model.Evaluation.module == module.id).
                        distinct()
                    ]
                    userdir = (
                        os.path.join(
                            "module_" + str(module.id),
                            util.submissions.strip_accents(user.first_name) +
                            "_" +
                            util.submissions.strip_accents(user.last_name)
                        )
                    ).replace(' ', '_')

                    files_added = 0

                    for fname in files:
                        if os.path.isfile(fname):
                            zipFile.write(
                                fname,
                                os.path.join(userdir, os.path.basename(fname))
                            )
                            files_added += 1
                        else:
                            get_log().warning(
                                "submFilesTask: soubor %s (module %d, user %d) "
                                "nenalezen na disku, preskakuji" %
                                (fname, module.id, user.id)
                            )

                    # Odevzdane kody programovacich modulu nejsou soubory
                    # na disku, ale text v databazi -- pridame je jako .txt.
                    if evaluation_ids:
                        codes = session.query(
                            model.SubmittedCode.evaluation,
                            model.SubmittedCode.code).\
                            filter(model.SubmittedCode.evaluation.
                                   in_(evaluation_ids)).all()
                        for evaluation_id, code in codes:
                            zipFile.writestr(
                                os.path.join(
                                    userdir,
                                    "code_%d.txt" % evaluation_id),
                                code if isinstance(code, str)
                                else code.decode('utf-8', 'replace')
                            )
                            files_added += 1

            zipFile.close()

            if files_added == 0:
                resp.status = falcon.HTTP_404
                req.context['result'] = {
                    'errors': [{
                        'status': '404',
                        'title': 'Not Found',
                        'detail': ('Pro tuto úlohu nebyla nalezena žádná '
                                   'odevzdání ke stažení.')
                    }]
                }
                return

            resp.set_header(
                'Content-Disposition',
                'inline; filename="task_' + str(task_id) + '.zip"'
            )
            resp.content_type = "application/zip"
            resp.body = inMemoryOutputFile.getvalue()
            resp.content_length = len(resp.body)

            inMemoryOutputFile.close()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
