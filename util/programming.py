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

# Default quotas for sandbox.
QUOTA_MEM = 5 * 10**7
QUOTA_WALL_TIME = 10
QUOTA_BLOCKS = 1000
QUOTA_INODES = 100
QUOTA_FILE_SIZE = 50000  # in kilobytes
OUTPUT_MAX_LEN = 5000  # in bytes


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
    if ("version" not in prog_info or
            _parse_version(prog_info["version"])[0] < 2):
        reporter += "Unsupported programming version %s\n"
        return (False, 'Opravení této úlohy není webovým systémem '
                'podporováno.')

    try:
        box_id = init_exec_environment()
    except ENoFreeBox:
        reporter += "Reached limit of concurrent tasks!\n"
        return (False, 'Přesáhnut maximální počet zároveň spuštěných opravení,'
                ' zkuste to později.')

    try:
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
            store_exec(box_id, user_id, module.id)
    finally:
        cleanup_exec_environment(box_id)

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


def store_exec(box_id, user_id, module_id):
    """
    Saves execution permanently to STORE_PATH directory.
    """
    src_path = os.path.abspath(os.path.join(EXEC_PATH, box_id))
    dst_path = os.path.abspath(os.path.join(STORE_PATH,
                                            "module_" + str(module_id),
                                            "user_" + str(user_id)))

    if os.path.isdir(dst_path):
        shutil.rmtree(dst_path)

    shutil.copytree(src_path, dst_path)


def _parse_version(version):
    v = version.split(".")
    return (int(v[0]), int(v[1]))


def run(module, user_id, code, reporter):
    """
    Manages whole process of running participant`s code.
    """
    prog_info = json.loads(module.data)['programming']
    if ("version" not in prog_info or
            _parse_version(prog_info["version"])[0] < 2):
        reporter += "Unsupported programming version %s\n"
        return {'output': 'Opravení této úlohy není webovým systémem '
                'podporováno.'}

    try:
        box_id = init_exec_environment()
    except ENotFreeBox as e:
        reporter += str(e) + "\n"
        return {'output': 'Přesáhnut maximální počet zároveň spuštěných úloh,'
                ' zkuste to později.'}

    try:
        try:
            res = _run(prog_info, code, box_id, reporter)
        finally:
            store_exec(box_id, user_id, module.id)
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
        trigger_stdout = _post_trigger(sandbox_root,
                                       prog_info['post_trigger_script'],
                                       reporter)

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

    with open(stdout_path, 'w') as stdout,\
            open(stderr_path, 'w') as stderr:
        p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, cwd=wd)
        p.wait()

    if p.returncode != 0:
        status = 'n'

    if not os.path.exists(code_merged):
        reporter += '\n Error: merge script did not create merged file!\n'
        raise FileNotFoundError("Merge script did not create merged file!")

    # Add executable flag to merged code
    st = os.stat(code_merged)
    os.chmod(code_merged, st.st_mode | stat.S_IEXEC)


def _exec(sandbox_dir, box_id, filename, stdin_path, reporter):
    """
    Executes single file inside a sandbox.
    """
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
        "-Mmeta",
        "-m" + str(QUOTA_MEM),
        "-w" + str(QUOTA_WALL_TIME),
        "--fsize=" + str(QUOTA_FILE_SIZE),
        "-q" + str(QUOTA_BLOCKS) + "," + str(QUOTA_INODES),
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

    with open(stdout_path, 'w') as stdout, open(stderr_path, 'w') as stderr:
        p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr,
                             cwd=sandbox_dir)
        p.wait()

    if os.path.getsize(stderr_path) > 0:
        reporter += "Check script returned nonempty stderr:\n"
        with open(stderr_path, 'r') as f:
            reporter += f.read()
        raise ECheckError("Check script returned non-empty stderr!")

    return p.returncode == 0
