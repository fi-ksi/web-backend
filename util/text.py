import json
import os

from db import session
import model
import subprocess

def num_fields(module):
	text = session.query(model.Text).filter(model.Text.module == module).first()
	return text.inputs

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
	report = '=== Evaluating text id \'%s\' for task id \'%s\' ===\n\n' % (module, task)
	report += ' Raw data: ' + json.dumps(data) + '\n'
	report += ' Evaluation:\n'

	text = session.query(model.Text).filter(model.Text.module == module).first()

	if text.diff:
		orig = json.loads(text.diff)
		result = True
		report += 'Diff used!\n'
		for o, item in zip(orig, data):
			s1 = o.rstrip().lstrip().encode('utf-8')
			s2 = item.rstrip().lstrip().encode('utf-8')
			if text.ignore_case:
				s1 = s1.lower()
				s2 = s2.lower()
			print("Compare: " + s1 + ", " + s2 +", " + str(s1 == s2))
			result = result and s1 == s2
		if len(data) != len(orig):
			result = False
		return (result, report)
	elif text.eval_script:
		return eval_text(text.eval_script, data, report)
	else:
		report += 'No eval method specified!\n'
		return (False, report)