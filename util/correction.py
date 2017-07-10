# -*- coding: utf-8 -*-

import datetime
from sqlalchemy import func, distinct, or_, and_, not_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util
import os

# Vraci seznam plne opravenych uloh (tj. takovych uloh, kde jsou vsechna reseni jiz opravena)
def tasks_corrected():
    task_corrected = session.query(model.Task.id.label('task_id'), (func.count(model.Evaluation.id) > 0).label('notcorrected')).\
        join(model.Module, model.Module.task == model.Task.id).\
        join(model.Evaluation, model.Module.id == model.Evaluation.module).\
        filter(model.Evaluation.evaluator == None, not_(model.Module.autocorrect)).\
        group_by(model.Task).subquery()

    return  [ r for (r, ) in session.query(model.Task.id).\
        outerjoin(task_corrected, task_corrected.c.task_id == model.Task.id).\
        filter(or_(task_corrected.c.notcorrected == False, task_corrected.c.notcorrected == None))
    ]

# Pomocny vypocet toho, jestli je dane hodnoceni opravene / neopravene
def corr_corrected(task_id, user_id):
    return session.query(model.Evaluation).\
        join(model.Module, model.Evaluation.module == model.Module.id).\
        filter(model.Evaluation.user == user_id, model.Module.task == task_id).\
        filter(or_(model.Module.autocorrect == True, model.Evaluation.evaluator != None)).count() > 0

# \files je nepovinny seznam souboru pro zmenseni poctu SQL dotazu
def _corr_general_to_json(module, evaluation, files=None):
    if files is None:
        files = session.query(model.SubmittedFile).\
            join(model.Evaluation, model.SubmittedFile.evaluation == evaluation.id).all()
    else:
        files = [smbfl for smbfl in files if smbfl.evaluation == evaluation.id]

    return {
        'files': [ {'id': inst.id, 'filename': os.path.basename(inst.path)} for inst in files ]
    }

# \files je seznam souboru pro souborovy modul
def corr_eval_to_json(module, evaluation, files=None):
    res = {
        'eval_id': evaluation.id,
        'points': evaluation.points,
        'last_modified': evaluation.time.isoformat(),
        'corrected_by': evaluation.evaluator,
        'full_report': evaluation.full_report
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

# U modulu se zobrazuje jen jedno evaluation:
#  Pokud to ma byt nejadekvatnejsi evaluation, je \evl=None.
#  Pokud to ma byt specificke evaluation, je toto evalustion ulozeno v \evl
# \files je seznam souboru pro souborovy modul
def _corr_module_to_json(evals, module, evl=None, files=None):
    if evl is None:
        # Ano, v Pythonu neexistuje max() pres dva klice
        evl = sorted(evals, key=lambda x: (x.points, x.time), reverse=True)[0]

    return {
        'module_id': module.id,
        'evaluations_list': [ evaluation.id for evaluation in evals ],
        'evaluation': corr_eval_to_json(module, evl, files)
    }

# \modules je [(Evaluation, Module, specific_eval)] a je seskupeno podle modulu
#  specific_eval je Evaluation pokud se ma klientovi poslat jen jedno evaluation
# \evals je [Evaluation]
# \achievements je [Ahievement.id]
# \corrected je Bool
# \files je seznam souboru
def to_json(modules, evals, task_id, thread_id=None, achievements=None, corrected=None, files=None):
    user_id = evals[0].user

    if thread_id is None: thread_id = util.task.comment_thread(task_id, user_id)
    if achievements is None: achievements = util.achievement.ids_list(util.achievement.per_task(user_id, task_id))
    if corrected is None: corrected = corr_corrected(task_id, user_id)

    return {
        'id': task_id*100000 + user_id,
        'task_id': task_id,
        'state': 'corrected' if corrected else 'notcorrected',
        'user': user_id,
        'comment': thread_id,
        'achievements': achievements,
        'modules': [ _corr_module_to_json([x for x in evals if x.module == module.id], module, spec_evl, files) for (evl, module, spec_evl) in modules ]
    }

def module_to_json(module):
    return {
        'id': module.id,
        'type': module.type,
        'name': module.name,
        'autocorrect': module.autocorrect,
        'max_points': module.max_points
    }

def task_to_json(task):
    return {
        'id': task.id,
        'title': task.title
    }
