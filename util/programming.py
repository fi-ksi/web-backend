# -*- coding: utf-8 -*-

import subprocess, traceback, os, shutil, json, ast, codecs, re, datetime
#from pypy_interact import PyPySandboxedProc
from humanfriendly import format_size
import stat

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

MODULE_LIB_PATH = 'data/module_lib/'
EXEC_PATH = '/tmp/box/'
MAX_CONCURRENT_EXEC = 10

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
        print(report)
        return ( 'error', 'Selhala operace _save_raw', '' )

    success, report = _merge(dir, programming['merge_script'], raw_code, merged_code, report)
    if not success:
        print(report)
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
        return ( 'exec-error', report, open(sandbox_stderr).read())

    #if programming.post_trigger_script:
    #   success, report, trigger_stdout = _post_trigger(dir, programming.post_trigger_script, sandbox_dir, report)

    success, report, result = _check(dir, programming['check_script'], sandbox_dir, sandbox_stdout, report)

    if success:
        return ('correct', report, '')
    else:
        return ('incorrect', report, '')

def find_free_exec_id() -> str:
    # Search for free id in EXEC_PATH
    ids = [ True for i in range(MAX_CONCURRENT_EXEC) ]
    for d in os.listdir(EXEC_PATH):
        if d.isdigit():
            ids[int(d)] = False

    for i in range(len(ids)):
        if ids[i]:
            return str(i)

    return None

def run(module, user_id, data):
    if not os.path.exists(EXEC_PATH):
        os.makedirs(EXEC_PATH)

    exec_id = find_free_exec_id()
    if exec_id is None:
        return ({'output': 'Přesáhnut maximální počet zároveň spuštěných úloh,'
            ' zkuste to později.' }, report)

    res = _run(module, user_id, data, exec_id)

    sandbox_root = os.path.join(EXEC_PATH, exec_id)
    if os.path.isdir(sandbox_root):
        p = subprocess.Popen([ "isolate", "-b", exec_id, "--cleanup"])
        p.wait()

    return res

def _run(module, user_id, data, exec_id):
    programming = json.loads(module.data)['programming']
    report = ''

    # Initialize sandbox
    p = subprocess.Popen([ "isolate", "-b", exec_id, "--init"])
    p.wait()
    if p.returncode != 0:
        report += "Error: isolate --init returned code " + str(p.returncode) + "\n"
        return ({'output': 'Nepovedlo se inicializovat sandbox, kontaktujte'
            'organizátora.'}, report)

    # Prepare files with participant`s code
    sandbox_root = os.path.join(EXEC_PATH, exec_id)
    raw_code = os.path.join(sandbox_root, 'raw')
    merged_code = os.path.join(sandbox_root, 'box', 'run')

    success, rep = _save_raw(data, raw_code, report)
    if not success:
        report += "Error: cannot save participant`s code:\n" + rep
        return ({ 'output': 'Selhalo uložení řešitelova kódu, kontaktujte '
            'organizátora.' }, report)

    # Merge participant`s code
    success, rep = _merge(sandbox_root, programming['merge_script'], raw_code,
        merged_code)
    report += rep + "\n"
    if not success:
        return ({ 'output': 'Selhala operace merge, kontaktujte organizátora.' },
            report)

    success, rep, output_path, meta_path, stderr_path = _exec(sandbox_root,
        exec_id, "/box/run", os.path.abspath(programming['stdin']))
    report += rep + "\n"

    trigger_data = None
    if ('post_trigger_script' in programming) and (programming['post_trigger_script']):
        post_success, rep, trigger_stdout = _post_trigger(dir,
            programming['post_trigger_script'], sandbox_dir, report)
        if not post_success:
            report += "Error: post trigger error:\n" + rep
            return ({ 'output': 'Selhal post trigger skript, prosím kontaktujte '
                'organizátora.' }, report)

        trigger_data = json.loads(open(trigger_stdout).read())
        if success:
            output = trigger_data['stdout']
        else:
            output = trigger_data['stdout'] + open(stderr_path).read()
    else:
        if success:
            output = open(output_path).read()
        else:
            output = open(output_path).read() + open(stderr_path).read()

    return ({
        'output': output,
        'image_output': '/images/codeExecution/%d?file=%s' % (execution.id,
            trigger_data['attachments'][0])
            if trigger_data and 'attachments' in trigger_data else None
    }, report)

def _save_raw(code, out, report):
    status = 'y'

    try:
        codecs.open(out, 'w', "utf-8").write(code)
    except IOError:
        save_status = 'n'

    report += '  [%s] Saving user code to %s\n' % (status, out)

    return (status == 'y', report)

def _merge(wd, merge_script, code, code_merged):
    cmd = [
        os.path.abspath(merge_script),
        os.path.abspath(code),
        os.path.abspath(code_merged),
        os.path.abspath(MODULE_LIB_PATH),
    ]

    stdout_path = os.path.join(wd, 'merge.stdout')
    stderr_path = os.path.join(wd, 'merge.stderr')
    exception = None

    report = 'Merging code to %s (cmd: %s)\n' % (code_merged, " ".join(cmd))
    report += ' * stdout: %s\n' % stdout_path
    report += ' * stderr: %s\n' % stderr_path

    try:
        stdout = open(stdout_path, 'w')
        stderr = open(stderr_path, 'w')
        process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=wd)
        process.wait()

        if process.returncode != 0:
            status = 'n'
    except BaseException:
        report += '\n __ Error report: __\n%s\n' % traceback.format_exc()
        return (False, report)

    if not os.path.exists(code_merged):
        report += '\n Error: merge script did not create merged file!\n'
        return ('n', report)

    # Add executable flag to merged code
    st = os.stat(code_merged)
    os.chmod(code_merged, st.st_mode | stat.S_IEXEC)

    return (True, report)

def _exec(sandbox_dir, box_id, filename, stdin):
    # TODO: default timeout
    timeout = 10

    stdout_path = os.path.join(sandbox_dir, "stdout")
    stderr_path = os.path.join(sandbox_dir, "stderr")
    output_path = os.path.join(sandbox_dir, "output")
    meta_path = os.path.join(sandbox_dir, "meta")

    cmd = [
        "isolate",
        "-b",
        box_id,
        "--dir=/etc=" + os.path.join(sandbox_dir, "etc"),
        "--env=LANG=C.UTF-8",
        "--run",
        filename,
    ]

    # Mockup /etc/passwd
    if not os.path.isdir(os.path.join(sandbox_dir, "etc")):
        os.mkdir(os.path.join(sandbox_dir, "etc"))
    with open(os.path.join(sandbox_dir, "etc", "passwd"), 'w') as f:
        f.write("tester:x:"+str(60000+int(box_id))+":0:Tester:/:\n")

    status = 'y'
    exception = None

    report = 'Running sandbox: %s\n' % (" ".join(cmd))
    report += ' * stdout: %s\n' % stdout_path
    report += ' * stderr: %s\n' % stderr_path

    try:
        start_time = datetime.datetime.now()
        p = subprocess.Popen(cmd, stdin=open(stdin, 'r'),
            stdout=open(stdout_path, 'w'), stderr=open(stderr_path, 'w'))
        p.wait()

        report += "Return code: %d\n" % (p.returncode)
        if p.returncode != 0:
            report += "Stdout: " +\
                open(stdout_path, 'r').read() + "\n"
            report += "Stderr: " +\
                open(stderr_path, 'r').read() + "\n"
            status = 'n'

        # Post process stdout
        with open(stdout_path, 'r') as f:
            lines = f.readlines()

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

        with open(output_path, 'w') as f:
            f.write(''.join(out))

        with open(meta_path, 'w') as f:
            f.write(''.join(data))

        # Post process stderr
        #_parse_stderr(stderr_path, timeout, datetime.datetime.now()-start_time, heaplimit)

    except BaseException:
        report += "Sandbox error:\n" +  traceback.format_exc()
        status = 'n'

    return (status == 'y', report, output_path, meta_path, stderr_path)

def _parse_stderr(filename, timeout, elapsed, heaplimit):
    with open(filename, "r") as f: content = f.read()

    killed = re.search(r"\[Subprocess killed by SIGTERM\]", content)
    memory = re.search(r"MemoryError", content)
    if killed or memory:
        report = "Program byl ukončen z důvodu vyčerpání přidělených prostředků.\n"
        report += "Časový limit: %d s, limit paměti: %s, čas běhu programu: %.2f s\n" % (timeout, format_size(heaplimit) if heaplimit else "-", elapsed.total_seconds())
        if elapsed.total_seconds() >= timeout: report += "Program překročil maximální čas běhu.\n"
        with codecs.open(filename, "a", "utf-8") as f: f.write(report)

def _post_trigger(wd, trigger_script, sandbox_dir, report):
    cmd = [ 'xvfb-run', '-a', '/usr/bin/python',
        os.path.abspath(trigger_script), os.path.abspath(sandbox_dir), os.path.abspath(MODULE_LIB_PATH) ]
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
    cmd = [ 'xvfb-run', '-e', os.path.join('err'), '-a', '/usr/bin/python',
        os.path.abspath(check_script), os.path.abspath(sandbox_dir),
        os.path.abspath(sandbox_stdout), os.path.abspath(MODULE_LIB_PATH) ]
    status = 'y'
    exception = None
    stdout_path = os.path.join(wd, 'check.stdout')
    stderr_path = os.path.join(wd, 'check.stdout')

    try:
        stdout = open(stdout_path, 'w')
        stderr = open(stderr_path, 'w')
        process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=wd)
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
