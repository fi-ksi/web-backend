# -*- coding: utf-8 -*-

import json
import os

from db import session
import model
import subprocess

"""
Specifikace \data v databazi modulu pro "text":
    text = {
        inputs = 3
        questions = ["otazka1", "otazka2", ...]
        diff = ["spravne_reseni_a", "spravne_reseni_b", "spravne_reseni_c"]
        eval_script = "/path/to/eval/script.py"
        ignore_case = True
    }
Kazdy modul muze mit jen jeden text (s vice inputy).
"""

def to_json(db_dict, user_id):
    if not 'questions' in db_dict['text']:
        # Stary format textoveho modulu (bez textu otazek) -> vytvorit texty
        # otazek.
        return { 'questions': [ 'Otázka '+str(i+1) for i in range(db_dict['text']['inputs']) ] }
    else:
        # Novy format vcetne textu otazek -> vratime texty otazek.
        return { 'questions': db_dict['text']['questions'] }

def eval_text(eval_script, data, report):
    cmd = ['/usr/bin/python', eval_script] + data
    f = open('/tmp/eval.txt', 'w')
    process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    process.wait()
    f.close();
    f = open('/tmp/eval.txt', 'r')
    report += f.read()

    return (process.returncode == 0, report)

def evaluate(task, module, data):
    report = '=== Evaluating text id \'%s\' for task id \'%s\' ===\n\n' % (module.id, task)
    report += ' Raw data: ' + json.dumps(data) + '\n'
    report += ' Evaluation:\n'

    text = json.loads(module.data)['text']

    if 'diff' in text:
        orig = text['diff']
        result = True
        report += 'Diff used!\n'
        for o, item in zip(orig, data):
            s1 = o.rstrip().lstrip().encode('utf-8')
            s2 = item.rstrip().lstrip().encode('utf-8')
            if ('ignore_case' in text) and (text['ignore_case']):
                s1 = s1.lower()
                s2 = s2.lower()
            result = result and s1 == s2
        if len(data) != len(orig):
            result = False
        return (result, report)
    elif 'eval_script' in text:
        return eval_text(text['eval_script'], data, report)
    else:
        report += 'No eval method specified!\n'
        return (False, report)
