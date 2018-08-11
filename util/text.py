import json
import os
import tempfile
import shutil

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

RESULT_FILE = 'eval.out'


class ECheckError(Exception):
    pass


def to_json(db_dict, user_id):
    if 'questions' not in db_dict['text']:
        # Stary format textoveho modulu (bez textu otazek) -> vytvorit texty
        # otazek.
        return {
            'questions': [
                'Otázka ' + str(i + 1)
                for i in range(db_dict['text']['inputs'])
            ]
        }
    else:
        # Novy format vcetne textu otazek -> vratime texty otazek.
        return {'questions': db_dict['text']['questions']}


def eval_text(eval_script, data, reporter):
    """ Evaluate text module by a script. """

    path = tempfile.mkdtemp()
    try:
        stdout_path = os.path.join(path, 'stdout')
        stderr_path = os.path.join(path, 'stderr')

        cmd = [os.path.abspath(eval_script)] + data

        with open(stdout_path, 'w') as stdout,\
                open(stderr_path, 'w') as stderr:
            p = subprocess.Popen(
                cmd,
                stdout=stdout,
                stderr=stderr,
                cwd=path
            )
            p.wait(timeout=10)  # seconds

        res = {'result': 'ok' if p.returncode == 0 else 'nok'}

        reporter += 'Stdout:\n'
        with open(stdout_path, 'r') as f:
            reporter += f.read()

        if os.path.getsize(stderr_path) > 0:
            reporter += 'Eval script returned nonempty stderr:\n'
            with open(stderr_path, 'r') as f:
                reporter += f.read()
            raise ECheckError('Eval script returned non-empty stderr!')

        # Load results from optional file.
        result_path = os.path.join(path, RESULT_FILE)
        if os.path.isfile(result_path):
            with open(result_path, 'r') as r:
                data = json.loads(r.read())

            if 'message' in data:
                res['message'] = data['message']

            if 'score' in data and res['result'] == 'ok':
                res['score'] = round(data['score'], 1)

        return res

    finally:
        if os.path.isdir(path):
            shutil.rmtree(path)


def evaluate(task, module, data, reporter):
    reporter += '=== Evaluating text id \'%s\' for task id \'%s\' ===\n\n' % (
          module.id, task)
    reporter += 'Raw data: ' + json.dumps(data) + '\n'
    reporter += 'Evaluation:\n'

    text = json.loads(module.data)['text']

    if 'diff' in text:
        orig = text['diff']
        result = True
        reporter += 'Diff used!\n'
        for o, item in zip(orig, data):
            s1 = o.rstrip().lstrip().encode('utf-8')
            s2 = item.rstrip().lstrip().encode('utf-8')
            if ('ignore_case' in text) and (text['ignore_case']):
                s1 = s1.lower()
                s2 = s2.lower()
            result = result and s1 == s2

        if len(data) != len(orig):
            result = False

        return {
            'result': 'ok' if result else 'nok'
        }

    elif 'eval_script' in text:
        return eval_text(text['eval_script'], data, reporter)

    else:
        reporter += 'No eval method specified!\n'
        return {
            'result': 'error',
            'message': 'Není dostupná žádná metoda opravení!'
        }
