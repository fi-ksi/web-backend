# -*- coding: utf-8 -*-

import json

from db import session
import model
import json

"""
Specifikace \data v databazi modulu pro "sortable":
    "sortable": {
        "style": -- zatim nepodporovano, planovano do budoucna

        "fixed": [{
            "content": String,
            "offset": Integer,
        }, {...}, ...]

        "movable": [
            vypada uplne stejne, jako "fixed"
        ]

        "correct": [[pole popisujici spravne poradi: napr. "b1", "a1", "a2", "b2" rika: nejdriv je prvni movable, pak prvni fixed, pak druhy fixed, pak druhy movable], [druhe_mozne_reseni]]
    }
"""

def to_json(db_dict, user_id):
    return {
        'fixed': db_dict['sortable']['fixed'],
        'movable': db_dict['sortable']['movable']
    }

def evaluate(task, module, data):
    report = '=== Evaluating sortable id \'%s\' for task id \'%s\' ===\n\n' % (module.id, task)
    report += ' Raw data: ' + json.dumps(data) + '\n'
    report += ' Evaluation:\n'

    sortable = json.loads(module.data)['sortable']
    user_order = data
    result = (user_order in sortable['correct'])

    report += '  User order: %s\n' % user_order
    report += '  Correct order: %s\n' % sortable['correct']
    report += '\n Overall result: [%s]' % ('y' if result else 'n')

    return (result, report)

