import subprocess
import traceback
import os
import shutil
import json
from pypy_interact import PyPySandboxedProc

from db import session
import model

def build(module_id):
	programming = session.query(model.Programming).filter(model.Programming.module == module_id).first()

	return programming.default_code

def evaluate(task, module, data):
	programming = session.query(model.Programming).filter(model.Programming.module == module.id).first()

	report = '=== Evaluating programming id \'%s\' for task id \'%s\' ===\n\n' % (module, task)
	report += ' Evaluation:\n'

	user_id = 14
	dir = 'submissions/module_%d/user_%d' % (programming.id, user_id)
	try:
		os.makedirs(dir)
	except OSError:
		pass

	raw_code = os.path.join(dir, 'code_raw.py')
	merged_code = os.path.join(dir, 'code_merged.py')

	success, report = _save_raw(data, raw_code, report)
	if not success:
		print report
		return

	success, report = _merge(dir, programming.merge_script, raw_code, merged_code, report)
	if not success:
		print report
		return

	sandbox_dir = os.path.join(dir, 'sandbox')
	try:
		os.mkdir(sandbox_dir)
	except OSError:
		pass
	script = os.path.join(sandbox_dir, 'code.py')
	shutil.copyfile(raw_code, script)

	(success, report, sandbox_stdout, sandbox_stderr) = _exec(dir, sandbox_dir, 'code.py', None, report)
	if not success:
		print report
		return

	(succes, report, result) = _check(dir, programming.check_script, sandbox_dir, sandbox_stdout, report)

	#print json.dumps(json.loads(open(result).read()))


	print report

def run(module, user_id, data):
	programming = session.query(model.Programming).filter(model.Programming.module == module.id).first()
	report = ''
	log = model.CodeExecution(module=module.id, user=user_id, code=data)

	session.add(log)
	session.commit()

	dir = os.path.join('data', 'code_executions', 'execution_%d' % log.id)
	try:
		os.makedirs(dir)
	except OSError:
		pass

	raw_code = os.path.join(dir, 'code_raw.py')
	merged_code = os.path.join(dir, 'code_merged.py')

	success, report = _save_raw(data, raw_code, report)
	if not success:
		return { 'output': 'Selhalo spusteni kodu (kod chyby: 1). Prosim kontaktujte organizatora' }

	success, report = _merge(dir, programming.merge_script, raw_code, merged_code, report)
	if not success:
		return { 'output': 'Selhalo spusteni kodu (kod chyby: 2). Prosim kontaktujte organizatora' }

	sandbox_dir = os.path.join(dir, 'sandbox')
	try:
		os.mkdir(sandbox_dir)
	except OSError:
		pass
	script = os.path.join(sandbox_dir, 'code.py')
	shutil.copyfile(raw_code, script)

	(success, report, sandbox_stdout, sandbox_stderr) = _exec(dir, sandbox_dir, 'code.py', None, report)

	return { 'output': open(sandbox_stdout if success else sandbox_stderr).read() }

def _save_raw(code, out, report):
	status = 'y'

	try:
		open(out, 'w').write(code)
	except IOError:
		save_status = 'n'

	report += '  [%s] Saving user code to %s\n' % (status, out)

	return (status == 'y', report)

def _merge(wd, merge_script, code, code_merged, report):
	status = 'y'
	cmd = [ '/usr/bin/python', merge_script, code, code_merged ]
	stdout_path = os.path.join(wd, 'merge.stdout')
	stderr_path = os.path.join(wd, 'merge.stdout')
	exception = None

	try:
		stdout = open(stdout_path, 'w')
		stderr = open(stderr_path, 'w')
		process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
		process.wait()

		if process.returncode != 0:
			status = 'n'
	except BaseException:
		exception = traceback.format_exc()
		status = 'n'

	report += '  [%s] Merging code to %s (cmd: %s)\n' % (status, code_merged, cmd)
	report += '   * stdout: %s\n' % stdout_path
	report += '   * stderr: %s\n' % stderr_path

	if exception:
		report += '\n __ Error report: __\n%s\n' % exception

	return (status == 'y', report)

def _exec(wd, sandbox_dir, script_name, stdin, report):
	status = 'y'
	exception = None
	stdout_path = os.path.join(wd, 'sandbox.stdout')
	stderr_path = os.path.join(wd, 'sandbox.stderr')
	log_path = os.path.join(wd, 'sandbox.log')

	try:
		stdout = open(stdout_path, 'w')
		stderr = open(stderr_path, 'w')
		sandproc = PyPySandboxedProc('/home/wormsik/src/pypy/pypy/goal/pypy-c', [ '/tmp/' + script_name ], tmpdir=sandbox_dir)
		sandproc.setlogfile(log_path)

		retcode = sandproc.interact(stdout=stdout, stderr=stderr)
		stdout.close()
		stderr.close()

		if retcode != 0:
			status = 'n'
	except BaseException:
		exception = traceback.format_exc()
		status = 'n'

	report += '  [%s] Running sandbox\n' % (status)
	report += '   * stdout: %s\n' % stdout_path
	report += '   * stderr: %s\n' % stderr_path

	if exception:
		report += '\n __ Error report: __\n%s\n' % exception

	return (status == 'y', report, stdout_path, stderr_path)

def _check(wd, check_script, sandbox_dir, sandbox_stdout, report):
	cmd = [ '/usr/bin/python', check_script, sandbox_dir, sandbox_stdout ]
	status = 'y'
	exception = None
	stdout_path = os.path.join(wd, 'check.stdout')
	stderr_path = os.path.join(wd, 'check.stdout')

	try:
		stdout = open(stdout_path, 'w')
		stderr = open(stderr_path, 'w')
		process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
		process.wait()

		if process.returncode != 0:
			status = 'n'
	except BaseException:
		exception = traceback.format_exc()
		status = 'n'

	report += '  [%s] Checking output (cmd: %s)\n' % (status, cmd)
	report += '   * stdout: %s\n' % stdout_path
	report += '   * stderr: %s\n' % stderr_path

	if exception:
		report += '\n __ Error report: __\n%s\n' % exception

	return (status == 'y', report, stdout_path)
