import subprocess
import traceback
import os
import shutil
import json
import ast
from pypy_interact import PyPySandboxedProc

from db import session
import model

def build(module_id):
	programming = session.query(model.Programming).filter(model.Programming.module == module_id).first()

	return programming.default_code

def evaluate(task, module, data):
	programming = session.query(model.Programming).filter(model.Programming.module == module.id).first()

	report = '=== Evaluating programming id \'%s\' for task id \'%s\' ===\n\n' % (module.id, task)
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

	(success, report, sandbox_stdout, sandbox_stderr) = _exec(dir, sandbox_dir, 'code.py', programming.args, programming.stdin, programming.timeout, report)
	if not success:
		print report
		return

	if programming.post_trigger_script:
		success, report, trigger_stdout = _post_trigger(dir, programming.post_trigger_script, sandbox_dir, report)

	success, report, result = _check(dir, programming.check_script, sandbox_dir, sandbox_stdout, report)

	return (success, report)

def code_execution_dir(execution_id):
	return os.path.join('data', 'code_executions', 'execution_%d' % execution_id)

def run(module, user_id, data):
	programming = session.query(model.Programming).filter(model.Programming.module == module.id).first()
	report = ''
	log = model.CodeExecution(module=module.id, user=user_id, code=data)

	session.add(log)
	session.commit()

	dir = code_execution_dir(log.id)
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

	success, report, sandbox_stdout, sandbox_stderr = _exec(dir, sandbox_dir, 'code.py', programming.args, programming.stdin, programming.timeout, report)

	trigger_data = None
	if success and programming.post_trigger_script:
		success, report, trigger_stdout = _post_trigger(dir, programming.post_trigger_script, sandbox_dir, report)
		if not success:
			return { 'output': 'Selhalo spusteni kodu (kod chyby: 3). Prosim kontaktujte organizatora' }

		trigger_data = json.loads(open(trigger_stdout).read())

	return {
		'output': open(sandbox_stdout if success else sandbox_stderr).read(),
		'image_output': '/images/codeExecution/%d?file=%s' % (log.id, trigger_data['attachments'][0]) if trigger_data else None
	}

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

def _exec(wd, sandbox_dir, script_name, args, stdin, timeout, report):
	status = 'y'
	exception = None
	stdout_path = os.path.join(wd, 'sandbox.stdout')
	stderr_path = os.path.join(wd, 'sandbox.stderr')
	args = [ '/tmp/' + script_name ] + ast.literal_eval(args) if args else []

	try:
		stdout = open(stdout_path, 'w')
		stderr = open(stderr_path, 'w')
		stdin = open(stdin) if stdin else sys.stdin
		sandproc = PyPySandboxedProc(os.path.join(os.path.expanduser('~'), 'pypy', 'pypy', 'goal', 'pypy-c'), args, tmpdir=sandbox_dir, debug=False)
		sandproc.settimeout(timeout, interrupt_main=True)

		retcode = sandproc.interact(stdin=stdin, stdout=stdout, stderr=stderr)
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

def _post_trigger(wd, trigger_script, sandbox_dir, report):
	cmd = [ '/usr/bin/python', os.path.abspath(trigger_script), sandbox_dir ]
	status = 'y'
	exception = None
	stdout_path = os.path.join(wd, 'post_trigger.stdout')
	stderr_path = os.path.join(wd, 'post_trigger.stderr')

	try:
		stdout = open(stdout_path, 'w')
		stderr = open(stderr_path, 'w')
		process = subprocess.Popen(cmd, cwd=wd, stdout=stdout, stderr=stderr)
		process.wait()

		if process.returncode != 0:
			status = 'n'
	except BaseException:
		traceback.print_exc()
		exception = traceback.format_exc()
		status = 'n'

	report += '  [%s] Running post trigger (cmd: %s)\n' % (status, cmd)
	report += '   * stdout: %s\n' % stdout_path
	report += '   * stderr: %s\n' % stderr_path

	if exception:
		report += '\n __ Error report: __\n%s\n' % exception

	return (status == 'y', report, stdout_path)

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
