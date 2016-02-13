# -*- coding: utf-8 -*-

import subprocess, traceback, os, shutil, json, ast, codecs, re, datetime
from pypy_interact import PyPySandboxedProc
from humanfriendly import format_size

from db import session
import model
import util

"""
Specifikace \data v databazi modulu pro "programming":
		"programming": {
			"default_code": Text,
			"merge_script": Text (path/to/merge/script.py),
			"stdin": Text,
			"args": "[]", <- tento argument je nepovinny
			"timeout": Integer, <- tento argument je nepovinny
			"post_trigger_script": Text, (path/to/post-triggger-script.py), <- tento argument je nepovinny
			"check_script": Text (path/to/check/script)
		}
"""

def to_json(db_dict, user_id):
	return { 'default_code': db_dict['programming']['default_code'] }

def evaluate(task, module, user_id, data):
	programming = json.loads(module.data)['programming']

	report = '=== Evaluating programming id \'%s\' for task id \'%s\' ===\n\n' % (module.id, task)
	report += ' Evaluation:\n'

	dir = util.module.submission_dir(module.id, user_id)
	try:
		os.makedirs(dir)
	except OSError:
		pass

	raw_code = os.path.join(dir, 'code_raw.py')
	merged_code = os.path.join(dir, 'code_merged.py')

	success, report = _save_raw(data, raw_code, report)
	if not success:
		print report
		return ( 'error', 'Selhala operace _save_raw', '' )

	success, report = _merge(dir, programming['merge_script'], raw_code, merged_code, report)
	if not success:
		print report
		return ( 'error', 'Selhala operace _merge', '' )

	sandbox_dir = os.path.abspath(os.path.join(dir, 'sandbox'))
	try:
		os.mkdir(sandbox_dir)
	except OSError:
		pass
	script = os.path.join(sandbox_dir, 'code.py')
	shutil.copyfile(merged_code, script)

	if not 'args' in programming: programming['args'] = []
	if not 'timeout' in programming: programming['timeout'] = 5
	if not 'heaplimit' in programming: programming['heaplimit'] = None

	(success, report, sandbox_stdout, sandbox_stderr) = _exec(dir, sandbox_dir, 'code.py', programming['args'], programming['stdin'], programming['timeout'], programming['heaplimit'], report)
	if not success:
		return ( 'exec-error', report, open(sandbox_stderr).read().decode('utf-8'))

	#if programming.post_trigger_script:
	#	success, report, trigger_stdout = _post_trigger(dir, programming.post_trigger_script, sandbox_dir, report)

	success, report, result = _check(dir, programming['check_script'], sandbox_dir, sandbox_stdout, report)

	if success:
		return ('correct', report, '')
	else:
		return ('incorrect', report, '')

def code_execution_dir(execution_id):
	return os.path.join('data', 'code_executions', 'execution_%d' % execution_id)

def run(module, user_id, data):
	programming = json.loads(module.data)['programming']
	report = ''
	log = model.CodeExecution(module=module.id, user=user_id, code=data)

	try:
		session.add(log)
		session.commit()
	except:
		session.rollback()
		raise

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

	success, report = _merge(dir, programming['merge_script'], raw_code, merged_code, report)
	if not success:
		return { 'output': 'Selhalo spusteni kodu (kod chyby: 2). Prosim kontaktujte organizatora' }

	sandbox_dir = os.path.abspath(os.path.join(dir, 'sandbox'))
	try:
		os.mkdir(sandbox_dir)
	except OSError:
		pass
	script = os.path.join(sandbox_dir, 'code.py')
	shutil.copyfile(merged_code, script)

	if not 'args' in programming: programming['args'] = []
	if not 'timeout' in programming: programming['timeout'] = 5
	if not 'heaplimit' in programming: programming['heaplimit'] = None

	success, report, sandbox_stdout, sandbox_stderr = _exec(dir, sandbox_dir, 'code.py', programming['args'], programming['stdin'], programming['timeout'], programming['heaplimit'], report)

	trigger_data = None
	if ('post_trigger_script' in programming) and (programming['post_trigger_script']):
		post_success, report, trigger_stdout = _post_trigger(dir, programming['post_trigger_script'], sandbox_dir, report)
		if not post_success:
			return { 'output': 'Selhalo spusteni kodu (kod chyby: 3). Prosim kontaktujte organizatora' }

		trigger_data = json.loads(open(trigger_stdout).read())
		if success:
			output = trigger_data['stdout']
		else:
			output = trigger_data['stdout'] + open(sandbox_stderr).read().decode('utf-8')
	else:
		if success:
			output = open(sandbox_dir+"/stdout").read().decode('utf-8')
		else:
			output = open(sandbox_dir+"/stdout").read().decode('utf-8') + open(sandbox_stderr).read().decode('utf-8')

	return {
		'output': output,
		'image_output': '/images/codeExecution/%d?file=%s' % (log.id, trigger_data['attachments'][0]) if trigger_data and 'attachments' in trigger_data else None
	}

def _save_raw(code, out, report):
	status = 'y'

	try:
		codecs.open(out, 'w', "utf-8").write(code)
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

def _exec(wd, sandbox_dir, script_name, args, stdin, timeout, heaplimit, report):
	status = 'y'
	exception = None
	stdout_path = os.path.join(wd, 'sandbox.stdout')
	stderr_path = os.path.join(wd, 'sandbox.stderr')
	output_path = os.path.join(sandbox_dir, 'output')
	soutput_path = os.path.join(sandbox_dir, 'stdout')

	margs = []
	if heaplimit: margs += [ "--heapsize", str(heaplimit) ]
	margs += [ '/tmp/' + script_name ]
	if args: margs += args

	try:
		start_time = datetime.datetime.now()
		stdout = open(stdout_path, 'w')
		stderr = open(stderr_path, 'w')
		stdin = open(stdin) if stdin else sys.stdin
		sandproc = PyPySandboxedProc(os.path.join(os.path.expanduser('~'), 'pypy', 'pypy', 'goal', 'pypy-c'), margs, tmpdir=sandbox_dir, debug=False)
		sandproc.settimeout(timeout, interrupt_main=True)

		retcode = sandproc.interact(stdin=stdin, stdout=stdout, stderr=stderr)
		stdout.close()
		stderr.close()

		if retcode != 0: status = 'n'

		# Post process stdout
		stdout = open(stdout_path, 'r')
		lines = stdout.readlines()
		stdout.close()

		out = []
		data = []

		found = False
		for line in lines:
			if found:
				data.append(line)
			else:
				if '#KSI_META_OUTPUT_0a859a#' in line:
					found = True
				else:
					out.append(line)

		stdout = open(soutput_path, 'w')
		stdout.write(''.join(out))
		stdout.close()

		meta = open(output_path, 'w')
		meta.write(''.join(data))
		meta.close()

		# Post process stderr
		_parse_stderr(stderr_path, timeout, datetime.datetime.now()-start_time, heaplimit)

	except BaseException:
		exception = traceback.format_exc()
		status = 'n'

	report += '  [%s] Running sandbox\n' % (status)
	report += '   * stdout: %s\n' % stdout_path
	report += '   * stderr: %s\n' % stderr_path

	if exception:
		report += '\n __ Error report: __\n%s\n' % exception

	return (status == 'y', report, stdout_path, stderr_path)

def _parse_stderr(filename, timeout, elapsed, heaplimit):
	with open(filename, "r") as f: content = f.read()

	killed = re.search(r"\[Subprocess killed by SIGTERM\]", content)
	memory = re.search(r"MemoryError", content)
	if killed or memory:
		report = u"Program byl ukončen z důvodu vyčerpání přidělených prostředků.\n"
		report += u"Časový limit: %d s, limit paměti: %s, čas běhu programu: %.2f s\n" % (timeout, format_size(heaplimit) if heaplimit else "-", elapsed.total_seconds())
		if elapsed.total_seconds() >= timeout: report += u"Program překročil maximální čas běhu.\n"
		with codecs.open(filename, "a", "utf-8") as f: f.write(report)

def _post_trigger(wd, trigger_script, sandbox_dir, report):
	cmd = [ 'xvfb-run', '-a', '/usr/bin/python', os.path.abspath(trigger_script), sandbox_dir ]
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
	cmd = [ 'xvfb-run', '-e', os.path.join('err'), '-a', '/usr/bin/python', check_script, sandbox_dir, sandbox_stdout ]
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
