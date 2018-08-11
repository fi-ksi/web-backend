import datetime
from humanfriendly import format_size, parse_timespan, parse_size
import json
import os
import shutil
import stat
import traceback
import subprocess
from sqlalchemy import desc

from db import session
import model
import util

"""
Specifikace \data v databazi modulu pro "programming":
        "programming": {
            "version": Text, <- default: 1.0
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
MAX_CONCURRENT_EXEC = 3
STORE_PATH = 'data/exec/'
SOURCE_FILE = 'source'
RESULT_FILE = 'eval.out'

# Default quotas for sandbox.
QUOTA_MEM = "50M"
QUOTA_WALL_TIME = "5s"
QUOTA_BLOCKS = 100
QUOTA_INODES = 100
QUOTA_FILE_SIZE = "50M"
OUTPUT_MAX_LEN = 5000  # in bytes


class ENoFreeBox(Exception):
    pass


class EIsolateError(Exception):
    pass


class EPostTriggerError(Exception):
    pass


class ECheckError(Exception):
    pass


class EMergeError(Exception):
    pass


class Reporter(object):
    def __init__(self):
        self.report = ""

    def __iadd__(self, other):
        self.report += other
        return self


def to_json(db_dict, user_id, module_id, last_eval):
    code = {
        'default_code': db_dict['programming']['default_code'],
        'code': db_dict['programming']['default_code'],
    }

    # Pick last participant`s code and return it to participant.
    if last_eval is not None:
        submitted = session.query(model.SubmittedCode).\
            filter(model.SubmittedCode.evaluation == last_eval.id).\
            first()

        if submitted is not None:
            code['code'] = submitted.code
            code['last_datetime'] = last_eval.time
            code['last_origin'] = 'evaluation'
    else:
        execution = session.query(model.CodeExecution).\
            filter(model.CodeExecution.module == module_id,
                   model.CodeExecution.user == user_id).\
            order_by(desc(model.CodeExecution.time)).\
            first()

        if execution is not None:
            code['code'] = execution.code
            code['last_datetime'] = execution.time
            code['last_origin'] = 'execution'

    return code


def exec_to_json(ex):
    return {
        'id': ex.id,
        'module': ex.module,
        'user': ex.user,
        'code': ex.code,
        'result': ex.result,
        'time': str(ex.time),
        'report': ex.report,
    }


def evaluate(task, module, user_id, code, eval_id, reporter):
    """
    Evaluates task. Runs merge, runs code, runs post trigger if necessary, runs
    check script.

    """

    prog_info = json.loads(module.data)['programming']
    if ("version" not in prog_info or
            _parse_version(prog_info["version"])[0] < 2):
        reporter += "Unsupported programming version %s\n"
        return {
            'result': 'error',
            'message': 'Opravení této úlohy není webovým systémem '
                       'podporováno.',
        }

    try:
        box_id = init_exec_environment()
    except ENoFreeBox:
        reporter += "Reached limit of concurrent tasks!\n"
        return {
            'result': 'error',
            'message': 'Přesáhnut maximální počet zároveň spuštěných opravení,'
                       ' zkuste to později.'
        }

    check_res = {}
    try:
        try:
            res = _run(prog_info, code, box_id, reporter)

            if res["code"] == 0:
                check_res = _check(os.path.join(EXEC_PATH, box_id),
                                   prog_info['check_script'],
                                   os.path.join(EXEC_PATH, box_id, "output"),
                                   reporter, user_id)
            else:
                return {
                    'result': 'nok',
                    'message': 'Tvůj kód se nepodařilo spustit, oprav si '
                               'chyby!',
                    'stdout': res['stdout'],
                }
        finally:
            store_exec(box_id, user_id, module.id,
                       'evaluation\n' + str(eval_id) + '\n')

    finally:
        cleanup_exec_environment(box_id)

    res = {
        'result': 'ok' if res['code'] == 0 and check_res['success'] else 'nok',
        'stdout': res['stdout'],
    }

    if 'message' in check_res:
        res['message'] = check_res['message']

    if ('score' in check_res and check_res['score'] <= module.max_points
            and check_res['score'] >= 0):
        res['score'] = check_res['score']
    else:
        res['score'] = module.max_points if res['result'] == 'ok' else 0

    return res


def find_free_box_id() -> str:
    """
    limits = prog_info["limits"] if "limits" in prog_info else {}
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
    """ Initializes sandbox. """

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
    """ Cleans up sandbox data. """

    sandbox_root = os.path.join(EXEC_PATH, box_id)
    if os.path.isdir(sandbox_root):
        p = subprocess.Popen(["isolate", "-b", box_id, "--cleanup"])
        p.wait()


def store_exec(box_id, user_id, module_id, source):
    """ Saves execution permanently to STORE_PATH directory. """

    src_path = os.path.abspath(os.path.join(EXEC_PATH, box_id))
    dst_path = os.path.abspath(os.path.join(STORE_PATH,
                                            "module_" + str(module_id),
                                            "user_" + str(user_id)))

    if os.path.isdir(dst_path):
        shutil.rmtree(dst_path)

    shutil.copytree(src_path, dst_path)

    # Write evaluation id so we can recognize it in the future
    with open(os.path.join(dst_path, SOURCE_FILE), 'w') as s:
        s.write(source)


def _parse_version(version):
    v = version.split(".")
    return (int(v[0]), int(v[1]))


def run(module, user_id, code, exec_id, reporter):
    """ Manages whole process of running participant`s code. """

    prog_info = json.loads(module.data)['programming']
    if ("version" not in prog_info or
            _parse_version(prog_info["version"])[0] < 2):
        reporter += "Unsupported programming version %s\n"
        return {
            'message': 'Opravení této úlohy není webovým systémem '
                       'podporováno.',
            'result': 'error',
        }

    try:
        box_id = init_exec_environment()
    except ENoFreeBox as e:
        reporter += str(e) + "\n"
        return {
            'message': 'Přesáhnut maximální počet zároveň spuštěných úloh,'
                       ' zkuste to později.',
            'result': 'error',
        }

    try:
        try:
            res = _run(prog_info, code, box_id, reporter, user_id)
        finally:
            store_exec(box_id, user_id, module.id,
                       'execution\n' + str(exec_id) + '\n')
    finally:
        cleanup_exec_environment(box_id)

    return {
        'stdout': res['stdout'],
        'result': 'ok',
    }


def _run(prog_info, code, box_id, reporter, user_id):
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
           reporter, user_id)

    limits = prog_info["limits"] if "limits" in prog_info else {}

    (return_code, output_path, secret_path, stderr_path) = _exec(
        sandbox_root, box_id, "/box/run", os.path.abspath(prog_info['stdin']),
        reporter, limits)

    trigger_data = None
    if ((return_code == 0) and ('post_trigger_script' in prog_info) and
            (prog_info['post_trigger_script'])):
        trigger_stdout = _post_trigger(sandbox_root,
                                       prog_info['post_trigger_script'],
                                       reporter, user_id)

        with open(trigger_stdout) as f:
            trigger_data = json.loads(f.read(OUTPUT_MAX_LEN))

        output = trigger_data['stdout']
    else:
        if return_code == 0:
            with open(output_path, 'r') as f:
                output = f.read(OUTPUT_MAX_LEN)

        else:
            with open(output_path, 'r') as output,\
                    open(stderr_path, 'r') as stderr:
                output = output.read(OUTPUT_MAX_LEN) + "\n" +\
                         stderr.read(OUTPUT_MAX_LEN)

    if len(output) >= OUTPUT_MAX_LEN:
        output += "\nOutput too long, stripped!\n"

    return {
        'stdout': output,
        'code': return_code,
    }


def _merge(wd, merge_script, code, code_merged, reporter, user_id):
    """ Runs merge script. """

    cmd = [
        os.path.abspath(merge_script),
        os.path.abspath(code),
        os.path.abspath(code_merged),
        os.path.abspath(MODULE_LIB_PATH),
        str(user_id),
    ]

    stdout_path = os.path.join(wd, 'merge.stdout')
    stderr_path = os.path.join(wd, 'merge.stderr')

    reporter += 'Merging code to %s (cmd: %s)\n' % (code_merged, " ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    with open(stdout_path, 'w') as stdout,\
            open(stderr_path, 'w') as stderr:
        p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=wd)
        p.wait()

    if p.returncode != 0:
        reporter += '\nError: Merge script exited with nonzero return code!\n'
        reporter += 'Stderr:\n'
        with open(stderr_path, 'r') as stderr:
            reporter += stderr.read()
        raise EMergeError("Merge script exited with nonzero return code!")

    if not os.path.exists(code_merged):
        reporter += '\nError: merge script did not create merged file!\n'
        raise FileNotFoundError("Merge script did not create merged file!")

    # Add executable flag to merged code
    st = os.stat(code_merged)
    os.chmod(code_merged, st.st_mode | stat.S_IEXEC)


def _exec(sandbox_dir, box_id, filename, stdin_path, reporter, limits):
    """ Executes single file inside a sandbox. """

    stdout_path = os.path.join(sandbox_dir, "stdout")
    stderr_path = os.path.join(sandbox_dir, "stderr")
    output_path = os.path.join(sandbox_dir, "output")
    secret_path = os.path.join(sandbox_dir, "secret")

    if "mem" not in limits:
        limits["mem"] = QUOTA_MEM

    if "total_time" not in limits:
        limits["total_time"] = QUOTA_WALL_TIME

    if "file_size" not in limits:
        limits["file_size"] = QUOTA_FILE_SIZE

    if "blocks" not in limits:
        limits["blocks"] = QUOTA_BLOCKS

    if "inodes" not in limits:
        limits["inodes"] = QUOTA_INODES

    cmd = [
        "isolate",
        "-b",
        box_id,
        "--dir=/etc=" + os.path.join(sandbox_dir, "etc"),
        "--env=LANG=C.UTF-8",
        "-Mmeta",
        "-m" + str(parse_size(limits["mem"])),
        "-w" + str(parse_timespan(limits["total_time"])),
        "--fsize=" + str(parse_size(limits["file_size"])//1000),
        "-q" + str(limits["blocks"]) + "," + str(limits["inodes"]),
    ]

    if "cpu_time" in limits:
        cmd.append("-t" + str(parse_timespan(limits["cpu_time"])))

    if "stack" in limits:
        cmd.append("-k" + str(parse_size(limits["stack"])//1000))

    if "processes" in limits:
        cmd.append("-p" + str(limits["processes"]))

    cmd += [
        "-c/box",
        "--run",
        filename,
    ]

    # Mock /etc/passwd
    if not os.path.isdir(os.path.join(sandbox_dir, "etc")):
        os.mkdir(os.path.join(sandbox_dir, "etc"))
    with open(os.path.join(sandbox_dir, "etc", "passwd"), 'w') as f:
        f.write("tester:x:" + str(60000 + int(box_id)) + ":0:Tester:/:\n")

    reporter += 'Running sandbox: %s\n' % (" ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    with open(stdin_path, 'r') as stdin, open(stdout_path, 'w') as stdout,\
            open(stderr_path, 'w') as stderr:
        start_time = datetime.datetime.now()
        p = subprocess.Popen(cmd, stdin=stdin, stdout=stdout,
                             stderr=stderr, cwd=sandbox_dir)
    p.wait()

    reporter += "Return code: %d\n" % (p.returncode)
    if p.returncode != 0:
        with open(stdout_path, 'r') as stdout:
            reporter += "Stdout: " + stdout.read() + "\n"
        with open(stderr_path, 'r') as stderr:
            reporter += "Stderr: " + stderr.read() + "\n"

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

    return (p.returncode, output_path, secret_path, stderr_path)


def _post_trigger(sandbox_dir, trigger_script, reporter, user_id):
    """ Runs post trigger script. """

    cmd = [
        os.path.abspath(trigger_script),
        os.path.abspath(sandbox_dir),
        os.path.abspath(MODULE_LIB_PATH),
        str(user_id),
    ]

    stdout_path = os.path.join(sandbox_dir, 'post_trigger.stdout')
    stderr_path = os.path.join(sandbox_dir, 'post_trigger.stderr')

    reporter += 'Running post trigger (cmd: %s)\n' % (" ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    with open(stdout_path, 'w') as stdout, open(stderr_path, 'w') as stderr:
        p = subprocess.Popen(cmd, cwd=sandbox_dir, stdout=stdout,
                             stderr=stderr)
        p.wait()

    if p.returncode != 0:
        reporter += "Post trigger script returned nonempty stderr:\n"
        with open(stderr_path, 'r') as f:
            reporter += f.read()
        raise EPostTriggerError("Post trigger returned code %d" %
                                (p.returncode))

    return stdout_path


def _check(sandbox_dir, check_script, sandbox_stdout, reporter, user_id):
    """ Runs check script. """

    cmd = [
        os.path.abspath(check_script),
        os.path.abspath(sandbox_dir),
        os.path.abspath(sandbox_stdout),
        os.path.abspath(MODULE_LIB_PATH),
        str(user_id),
    ]

    stdout_path = os.path.join(sandbox_dir, 'check.stdout')
    stderr_path = os.path.join(sandbox_dir, 'check.stderr')

    reporter += 'Checking output (cmd: %s)\n' % (" ".join(cmd))
    reporter += ' * stdout: %s\n' % stdout_path
    reporter += ' * stderr: %s\n' % stderr_path

    with open(stdout_path, 'w') as stdout, open(stderr_path, 'w') as stderr:
        p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr,
                             cwd=sandbox_dir)
        p.wait()

    res = {'success': (p.returncode == 0)}

    if os.path.getsize(stderr_path) > 0:
        reporter += "Check script returned nonempty stderr:\n"
        with open(stderr_path, 'r') as f:
            reporter += f.read()
        raise ECheckError("Check script returned non-empty stderr!")

    # Load results from optional file.
    result_path = os.path.join(sandbox_dir, RESULT_FILE)
    if os.path.isfile(result_path):
        with open(result_path, 'r') as r:
            data = json.loads(r.read())

        if 'message' in data:
            res['message'] = data['message']

        if 'score' in data and res['success']:
            res['score'] = round(data['score'], 1)

    return res
