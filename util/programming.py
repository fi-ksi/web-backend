import datetime
from humanfriendly import format_size
import json
import os
import shutil
import stat
import traceback
import subprocess

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
            "post_trigger_script": Text, (path/to/post-triggger-script.py),
                tento argument je nepovinny
            "check_script": Text (path/to/check/script)
        }
"""

MODULE_LIB_PATH = 'data/module_lib/'
EXEC_PATH = '/tmp/box/'
MAX_CONCURRENT_EXEC = 10


class ENoFreeBox(Exception):
    pass


class EIsolateError(Exception):
    pass


class EPostTriggerError(Exception):
    pass


class ECheckError(Exception):
    pass


class Reporter(object):
    def __init__(self):
        self.report = ""

    def __iadd__(self, other):
        self.report += other
        return self


def to_json(db_dict, user_id):
    return {'default_code': db_dict['programming']['default_code']}


def evaluate(task, module, user_id, code, reporter):
    """
    Evaluates task. Runs merge, runs code, runs post trigger if necessary, runs
    check script.
    """
    prog_info = json.loads(module.data)['programming']
    box_id = init_exec_environment()

    try:
        res = _run(prog_info, code, box_id, reporter)
        if res["code"] == 0:
            success = _check(os.path.join(EXEC_PATH, box_id),
                             prog_info['check_script'],
                             os.path.join(EXEC_PATH, box_id, "output"),
                             reporter)
        else:
            success = False
    finally:
        cleanup_exec_environment(box_id)
        pass

    return (success, res["output"])


def find_free_box_id() -> str:
    """
    Returns is of the first available sandbox directory. Searched for
    non-existing directories in /tmp/box.
    """
    # Search for free id in EXEC_PATH
    ids = [True for i in range(MAX_CONCURRENT_EXEC)]
    for d in os.listdir(EXEC_PATH):
        if d.isdigit():
            ids[int(d)] = False

    for i in range(len(ids)):
        if ids[i]:
            return str(i)

    return None


def init_exec_environment():
    """
    Initializes sandbox.
    """
    # Create directory for sandbox
    if not os.path.exists(EXEC_PATH):
        os.makedirs(EXEC_PATH)

    box_id = find_free_box_id()

    if box_id is None:
        raise ENoFreeBox("Reached limit of concurrent tasks!")

    # Run isolate --init
    p = subprocess.Popen(["isolate", "-b", box_id, "--init"])
    p.wait()
    if p.returncode != 0:
        raise EIsolateError("Isolate --init returned code " +
                            str(p.returncode))

    return box_id


def cleanup_exec_environment(box_id):
    """
    Cleans up sandbox data.
    """
    sandbox_root = os.path.join(EXEC_PATH, box_id)
    if os.path.isdir(sandbox_root):
        p = subprocess.Popen(["isolate", "-b", box_id, "--cleanup"])
        p.wait()


def run(module, user_id, code, reporter):
    """
    Manages whole process of running participant`s code.
    """
    # TODO: allow to preserve sandbox files to debug
    prog_info = json.loads(module.data)['programming']

    try:
        box_id = init_exec_environment()
    except ENotFreeBox as e:
        reporter += str(e) + "\n"
        return {'output': 'Přesáhnut maximální počet zároveň spuštěných úloh,'
                ' zkuste to později.'}
    except EIsolateError as e:
        reporter += str(e) + "\n"
        return {'output': 'Nepovedlo se inicializovat sandbox, kontaktujte'
                'organizátora.'}

    try:
        res = _run(prog_info, code, box_id, reporter)
    finally:
        cleanup_exec_environment(box_id)

    return res


def _run(prog_info, code, box_id, reporter):
    """
    Runs merge and runs the merged file inside of a sandbox. Requires
    initialized sandbox with id \box_id (str). \data is participant`s code.
    This function can throw exceptions, exceptions must be handled.
    """
    # Prepare files with participant`s code
    sandbox_root = os.path.join(EXEC_PATH, box_id)
    raw_code = os.path.join(sandbox_root, 'raw')
    merged_code = os.path.join(sandbox_root, 'box', 'run')

    # Save participant`s 'raw' code
    reporter += "Saving raw code into %s...\n" % (raw_code)
    with open(raw_code, "w") as f:
        f.write(code)

    # Merge participant`s code
    _merge(sandbox_root, prog_info['merge_script'], raw_code, merged_code,
           reporter)

    (return_code, output_path, secret_path, stderr_path) = _exec(
        sandbox_root, box_id, "/box/run", os.path.abspath(prog_info['stdin']),
        reporter)

    trigger_data = None
    if ((return_code == 0) and ('post_trigger_script' in prog_info) and
       (prog_info['post_trigger_script'])):
        trigger_stdout = _post_trigger(
            sandbox_dir, prog_info['post_trigger_script'], reporter)

        trigger_data = json.loads(open(trigger_stdout).read())
        output = trigger_data['stdout']
    else:
        if return_code == 0:
            output = open(output_path).read()
        else:
            output = open(output_path).read() + open(stderr_path).read()

    return {
        'output': output,
        'code': return_code,
        # 'image_output': '/images/codeExecution/%d?file=%s' % (execution.id,
        #    trigger_data['attachments'][0])
        #    if trigger_data and 'attachments' in trigger_data else None
        # TODO: encode image output as base64 image
    }


def _merge(wd, merge_script, code, code_merged, reporter):
    """
    Runs merge script.
    """
    cmd = [
        os.path.abspath(merge_script),
        os.path.abspath(code),
        os.path.abspath(code_merged),
        os.path.abspath(MODULE_LIB_PATH),
    ]

    stdout_path = os.path.join(wd, 'merge.stdout')
    stderr_path = os.path.join(wd, 'merge.stderr')

    reporter += 'Merging code to %s (cmd: %s)\n' % (code_merged, " ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    try:
        stdout = open(stdout_path, 'w')
        stderr = open(stderr_path, 'w')
        process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=wd)
        process.wait()

        if process.returncode != 0:
            status = 'n'
    except BaseException:
        reporter += '\n __ Error report: __\n%s\n' % traceback.format_exc()
        raise

    if not os.path.exists(code_merged):
        reporter += '\n Error: merge script did not create merged file!\n'
        raise FileNotFoundError("Merge script did not create merged file!")

    # Add executable flag to merged code
    st = os.stat(code_merged)
    os.chmod(code_merged, st.st_mode | stat.S_IEXEC)


def _exec(sandbox_dir, box_id, filename, stdin, reporter):
    """
    Executes single file inside a sandbox.
    """
    # TODO: default timeout
    timeout = 10

    stdout_path = os.path.join(sandbox_dir, "stdout")
    stderr_path = os.path.join(sandbox_dir, "stderr")
    output_path = os.path.join(sandbox_dir, "output")
    secret_path = os.path.join(sandbox_dir, "secret")

    cmd = [
        "isolate",
        "-b",
        box_id,
        "--dir=/etc=" + os.path.join(sandbox_dir, "etc"),
        "--env=LANG=C.UTF-8",
        "--run",
        filename,
    ]

    # Mock /etc/passwd
    if not os.path.isdir(os.path.join(sandbox_dir, "etc")):
        os.mkdir(os.path.join(sandbox_dir, "etc"))
    with open(os.path.join(sandbox_dir, "etc", "passwd"), 'w') as f:
        f.write("tester:x:"+str(60000+int(box_id))+":0:Tester:/:\n")

    reporter += 'Running sandbox: %s\n' % (" ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    try:
        start_time = datetime.datetime.now()
        p = subprocess.Popen(cmd, stdin=open(stdin, 'r'),
                             stdout=open(stdout_path, 'w'),
                             stderr=open(stderr_path, 'w'))
        p.wait()

        reporter += "Return code: %d\n" % (p.returncode)
        if p.returncode != 0:
            reporter += "Stdout: " +\
                open(stdout_path, 'r').read() + "\n"
            reporter += "Stderr: " +\
                open(stderr_path, 'r').read() + "\n"

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

        with open(secret_path, 'w') as f:
            f.write(''.join(data))

        # Post process stderr
        # _parse_stderr(stderr_path, timeout,
        #   datetime.datetime.now()-start_time, heaplimit)

    except:
        reporter += "Sandbox error:\n" + traceback.format_exc()
        raise

    return (p.returncode, output_path, secret_path, stderr_path)


def _parse_stderr(filename, timeout, elapsed, heaplimit):
    with open(filename, "r") as f:
        content = f.read()

    killed = re.search(r"\[Subprocess killed by SIGTERM\]", content)
    memory = re.search(r"MemoryError", content)
    if killed or memory:
        report = ("Program byl ukončen z důvodu vyčerpání "
                  "přidělených prostředků.\n")
        report += ("Časový limit: %d s, limit paměti: %s, čas běhu programu:"
                   " %.2f s\n" % (timeout, format_size(heaplimit)
                                  if heaplimit else "-",
                                  elapsed.total_seconds()))

        if elapsed.total_seconds() >= timeout:
            report += "Program překročil maximální čas běhu.\n"
        with codecs.open(filename, "a", "utf-8") as f:
            f.write(report)


def _post_trigger(sandbox_dir, trigger_script, reporter):
    """
    Runs post trigger script.
    """
    cmd = [
        os.path.abspath(trigger_script),
        os.path.abspath(sandbox_dir),
        os.path.abspath(MODULE_LIB_PATH),
    ]

    stdout_path = os.path.join(sandbox_dir, 'post_trigger.stdout')
    stderr_path = os.path.join(sandbox_dir, 'post_trigger.stderr')

    reporter += 'Running post trigger (cmd: %s)\n' % (" ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    try:
        stdout = open(stdout_path, 'w')
        stderr = open(stderr_path, 'w')
        p = subprocess.Popen(cmd, cwd=wd, stdout=stdout, stderr=stderr)
        p.wait()

        if p.returncode != 0:
            raise EPostTriggerError("Post trigger returned code %d" %
                                    (p.returncode))
    except Exception as e:
        reporter += str(e) + "\n"
        raise

    return stdout_path


def _check(sandbox_dir, check_script, sandbox_stdout, reporter):
    """
    Runs check script.
    """
    cmd = [
        os.path.abspath(check_script),
        os.path.abspath(sandbox_dir),
        os.path.abspath(sandbox_stdout),
        os.path.abspath(MODULE_LIB_PATH)
    ]

    stdout_path = os.path.join(sandbox_dir, 'check.stdout')
    stderr_path = os.path.join(sandbox_dir, 'check.stderr')

    reporter += 'Checking output (cmd: %s)\n' % (" ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    stdout = open(stdout_path, 'w')
    stderr = open(stderr_path, 'w')
    p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=sandbox_dir)
    p.wait()

    if os.path.getsize(stderr_path) > 0:
        reporter += "Check script returned nonempty stderr:\n"
        reporter += open(stderr_path, 'r').read()
        raise ECheckError("Check script returned non-empty stderr!")

    return p.returncode == 0
