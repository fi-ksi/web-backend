import datetime
import os
from typing import Dict, List, Optional, TypedDict, Tuple

from sqlalchemy import func, distinct, or_, and_, not_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util


# Vraci seznam plne opravenych uloh (tj. takovych uloh, kde jsou vsechna
# reseni jiz opravena)
def tasks_corrected() -> List[int]:
    task_corrected = session.query(
            model.Task.id.label('task_id'),
            (func.count(model.Evaluation.id) > 0).label('notcorrected')).\
        join(model.Module, model.Module.task == model.Task.id).\
        join(model.Evaluation, model.Module.id == model.Evaluation.module).\
        filter(model.Evaluation.evaluator == None,
               not_(model.Module.autocorrect)).\
        group_by(model.Task).subquery()

    return [r for (r, ) in session.query(model.Task.id).
        outerjoin(task_corrected, task_corrected.c.task_id == model.Task.id).
        filter(or_(task_corrected.c.notcorrected == False,
                   task_corrected.c.notcorrected == None))]


# Pomocny vypocet toho, jestli je dane hodnoceni opravene / neopravene
def corr_corrected(task_id: int, user_id: int) -> bool:
    return session.query(model.Evaluation).\
        join(model.Module, model.Evaluation.module == model.Module.id).\
        filter(model.Evaluation.user == user_id,
               model.Module.task == task_id).\
        filter(or_(model.Module.autocorrect == True,
                   model.Evaluation.evaluator != None)).count() > 0


class FileInfo(TypedDict):
    id: int
    filename: str


# \files je nepovinny seznam souboru pro zmenseni poctu SQL dotazu
def _corr_general_to_json(module: model.Module,
                          evaluation: model.Evaluation,
                          files: Optional[List[model.SubmittedFile]] = None)\
        -> Dict[str, List[FileInfo]]:
    if files is None:
        files = session.query(model.SubmittedFile).\
            join(model.Evaluation,
                 model.SubmittedFile.evaluation == evaluation.id).all()
    else:
        files = [smbfl for smbfl in files if smbfl.evaluation == evaluation.id]

    return {
        'files': [
            {'id': inst.id, 'filename': os.path.basename(inst.path)}
            for inst in files
        ]
    }


class CorrInfo(TypedDict):
    eval_id: int
    points: float
    last_modified: str
    corrected_by: int
    full_report: str
    cheat: bool
    general: Dict[str, List[FileInfo]]
    programming: Dict
    quiz: Dict
    sortable: Dict
    text: Dict


# \files je seznam souboru pro souborovy modul
def corr_eval_to_json(module: model.Module,
                      evaluation: model.Evaluation,
                      files: Optional[List[model.SubmittedFile]] = None)\
        -> CorrInfo:
    res = {
        'eval_id': evaluation.id,
        'points': evaluation.points,
        'last_modified': evaluation.time.isoformat(),
        'corrected_by': evaluation.evaluator,
        'full_report': evaluation.full_report,
        'cheat': evaluation.cheat,
    }

    if module.type == model.module.ModuleType.GENERAL:
        res['general'] = _corr_general_to_json(module, evaluation, files)
    elif module.type == model.module.ModuleType.PROGRAMMING:
        res['programming'] = {}
    elif module.type == model.module.ModuleType.QUIZ:
        res['quiz'] = {}
    elif module.type == model.module.ModuleType.SORTABLE:
        res['sortable'] = {}
    elif module.type == model.module.ModuleType.TEXT:
        res['text'] = {}

    return res


class ModuleCorr(TypedDict):
    module_id: int
    evaluations_list: List[int]
    evaluation: CorrInfo


# U modulu se zobrazuje jen jedno evaluation:
#  Pokud to ma byt nejadekvatnejsi evaluation, je \evl=None.
#  Pokud to ma byt specificke evaluation, je toto evalustion ulozeno v \evl
# \files je seznam souboru pro souborovy modul
def _corr_module_to_json(evals: List[model.Evaluation], module: model.Module,
                         evl: Optional[model.Evaluation] = None,
                         files: Optional[List[model.SubmittedFile]] = None)\
        -> ModuleCorr:
    if evl is None:
        # Ano, v Pythonu neexistuje max() pres dva klice
        evl = sorted(evals, key=lambda x: (x.points, x.time), reverse=True)[0]

    return {
        'module_id': module.id,
        'evaluations_list': [evaluation.id for evaluation in evals],
        'evaluation': corr_eval_to_json(module, evl, files)
    }


class CorrJson(TypedDict):
    id: int
    task_id: int
    state: str
    user: int
    comment: Optional[int]
    achievements: List[int]
    modules: List[ModuleCorr]


# \modules je [(Evaluation, Module, specific_eval)] a je seskupeno podle modulu
# specific_eval je Evaluation pokud se ma klientovi poslat jen jedno evaluation
# \evals je [Evaluation]
# \achievements je [Ahievement.id]
# \corrected je Bool
# \files je seznam souboru
def to_json(modules: List[Tuple[model.Evaluation,
                                model.Module,
                                Optional[model.Evaluation]]],
            evals: List[model.Evaluation],
            task_id: int,
            thread_id: Optional[int] = None,
            achievements: Optional[List[int]] = None,
            corrected: Optional[bool] = None,
            files: Optional[List[model.SubmittedFile]] = None) -> CorrJson:
    user_id = evals[0].user

    if thread_id is None:
        thread_id = util.task.comment_thread(task_id, user_id)
    if achievements is None:
        achievements = util.achievement.ids_list(
            util.achievement.per_task(user_id, task_id))
    if corrected is None:
        corrected = corr_corrected(task_id, user_id)

    return {
        'id': task_id*100000 + user_id,
        'task_id': task_id,
        'state': 'corrected' if corrected else 'notcorrected',
        'user': user_id,
        'comment': thread_id,
        'achievements': achievements,
        'modules': [
            _corr_module_to_json([x for x in evals if x.module == module.id],
                                 module, spec_evl, files)
            for (evl, module, spec_evl) in modules
        ],
    }


class ModuleJson(TypedDict):
    id: int
    type: str
    name: str
    autocorrect: bool
    max_points: float


def module_to_json(module: model.Module) -> ModuleJson:
    return {
        'id': module.id,
        'type': module.type,
        'name': module.name,
        'autocorrect': module.autocorrect,
        'max_points': module.max_points
    }


class TaskJson(TypedDict):
    id: int
    title: str


def task_to_json(task: model.Task) -> TaskJson:
    return {
        'id': task.id,
        'title': task.title
    }
