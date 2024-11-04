#!/usr/bin/env/python3

"""
Parses seminar repository and asks if it should create all found tasks that are not currently found on backend.
Requires following environment variables:
- REPO - path to the seminar repository
"""

import datetime
import re
import json
from time import sleep
from urllib import request
from pathlib import Path
from subprocess import check_output
from typing import Set, NamedTuple, Dict
from os import environ
from util_login import KSILogin


class MockKSITask(NamedTuple):
    title: str
    wave_id: int
    author: int
    git_path: str
    git_branch: str


def task_path_to_task(repo: Path, branch: str, task_path: str, waves: Dict[str, int]) -> MockKSITask:
    """
    Creates mock task that can be sent to the backend endpoint
    :param repo: path to the seminar repository
    :param branch: current branch of task
    :param task_path: path inside git
    :param waves: map of wave numbers to their ids
    :return: mock task
    """
    wave_number, task_name = extract_task_wave_and_number(task_path)
    assert wave_number in waves, f"This wave ({wave_number}) is not known"
    return MockKSITask(
        title=task_name,
        wave_id=waves[wave_number],
        author=extract_task_author(repo, branch, task_path),
        git_path=task_path,
        git_branch=branch
    )


def extract_task_wave_and_number(task_path: str) -> (str, str):
    """
    Extracts task name and wave number from the path root
    :param task_path: path inside git
    :return: task wave index and task name
    """
    re_task_meta = re.compile(r'^\d+/vlna([^/]+)/uloha_\d+_(.+)$')
    match = re_task_meta.match(task_path)
    assert match is not None, f"Invalid task root ({task_path})"
    wave_number = match.group(1)
    task_name = match.group(2).replace('_', ' ').capitalize()
    return wave_number, task_name


def fetch_known_waves(backend_url: str, token: str) -> Dict[int, str]:
    """
    Fetches all already known waves
    :param backend_url: url of the backend, including https
    :param token: login token
    :return: map of wave indexes to their names
    """
    with request.urlopen(request.Request(f"{backend_url}/waves", headers={'Authorization': token})) as res:
        waves = json.loads(res.read().decode('utf8'))['waves']
    return {x['id']: x['caption'] for x in waves}


def fetch_known_paths(backend_url: str, token: str) -> Set[str]:
    """
    Fetches all already known git paths
    :param backend_url: url of the backend, including https
    :param token: login token
    :return: set of all known git paths
    """
    with request.urlopen(request.Request(f"{backend_url}/admin/atasks", headers={'Authorization': token})) as res:
        tasks = json.loads(res.read().decode('utf8'))['atasks']
    return set(map(lambda x: x['git_path'], tasks))


def create_task(task: MockKSITask, backend_url: str, token: str) -> bool:
    """
    Creates a new task on the backend
    :param task: task to be created
    :param backend_url: url of the backend, including https
    :param token: login token
    :return: None
    """
    with request.urlopen(request.Request(
        f"{backend_url}/admin/atasks",
        headers={'Authorization': token, 'Content-Type': 'application/json'},
        data=json.dumps({'atask': {
            'wave': task.wave_id,
            'title': task.title,
            'author': task.author,
            'git_path': task.git_path,
            'git_branch': task.git_branch,
            'git_create': False
        }}).encode('utf8')
    )) as res:
        res.read()
    return True


def create_year(title: str, backend_url: str, token: str) -> int:
    """
    Creates a new year on the backend
    :param title: year to be created
    :param backend_url: url of the backend, including https
    :param token: login token
    :return: None
    """
    with request.urlopen(request.Request(
        f"{backend_url}/years",
        headers={'Authorization': token, 'Content-Type': 'application/json'},
        data=json.dumps({'id': None, 'year': title, 'sealed': False, 'point_pad': 0.0}).encode('utf8')
    )) as res:
        return json.loads(res.read())['year']['id']


def create_wave(title: str, year: int, garant: int, backend_url: str, token: str) -> int:
    """
    Creates a new wave on the backend
    :param title: wave name
    :param year: year id
    :param garant: garant id
    :param backend_url: url of the backend, including https
    :param token: login token
    :return: None
    """
    with request.urlopen(request.Request(
        f"{backend_url}/waves",
        headers={'Authorization': token, 'Content-Type': 'application/json', 'Year': str(year)},
        data=json.dumps({'caption': title, 'index': None, 'garant': garant, 'time_published': '2099-01-01'}).encode('utf8')
    )) as res:
        return res.read()['wave']['id']


def extract_task_author(repo: Path, branch: str, task_root: str) -> int:
    """
    Extracts author ID from task.json
    :param repo: path to the seminar repository
    :param branch: branch name to author from
    :param task_root: path inside git
    :return: author id
    """
    data = json.loads(check_output(['git', 'show', f"origin/{branch}:{task_root}/task.json"], text=True, cwd=repo))
    return int(data['author'])


def extract_task_paths(repo: Path, branch: str) -> Set[str]:
    """
    Extracts paths of all root directories of all tasks inside remote branch
    :param repo: path to the seminar repository
    :param branch: branch name to extract from
    :return: string paths to the root directories of all tasks inside given branch
    """
    re_task_path = re.compile(r'^(\d+/vlna[^/]+/uloha_\d+_.+?)/')
    paths = set()
    for line in check_output(['git', 'ls-tree', '-r', '--name-only', f'origin/{branch}'], text=True, cwd=repo).split('\n'):
        match = re_task_path.match(line)
        if match is None:
            continue
        paths.add(match.group(1))
    return paths


def extrack_task_paths_all(repo: Path, filter_year: str) -> Dict[str, str]:
    """
    Checks all branches for all task roots
    :param repo: path to the seminar repository
    :param filter_year: all roots must start with this prefix
    :return: task path -> task branch
    """
    data = {}

    for branch in check_output(['git', 'branch', '-a'], text=True, cwd=repo).split('\n'):
        branch = branch.strip()
        if not branch.startswith('remotes/origin/'):
            continue
        branch = branch.removeprefix('remotes/origin/')
        branch = branch.split(' -> ', 1)[0]  # fix for lines like remotes/origin/HEAD -> origin/master
        for path in extract_task_paths(repo, branch):
            if not path.startswith(filter_year):
                continue
            if not (repo / path / 'task.json').exists():
                continue
            data[path] = branch

    return data


def main() -> int:
    repo = Path(environ['REPO'])
    year = environ.get('YEAR', str((datetime.date.today() - datetime.timedelta(days=6*30)).year))
    print(f"Will import tasks from {repo} ({year})")

    login = KSILogin.login_auto()
    backend = (login.backend_url, login.token)
    print(f"Logged in to {backend[0]}")
    tasks_all = extrack_task_paths_all(repo, year)

    paths_known = fetch_known_paths(*backend)

    paths_new = tasks_all.keys() - paths_known
    print(f'Found {len(paths_new)} new tasks ({len(paths_known)} remote & {len(tasks_all)} local in total):')
    print('\n'.join(paths_new))
    print()
    assert input('OK? y/n ').strip().lower() == 'y', "Ok, bye"

    wave_map_name_id = fetch_known_waves(*backend)

    wave_mapping: Dict[str, int] = {}

    for task_path in sorted(tasks_all.keys()):
        task_branch = tasks_all[task_path]
        if task_path not in paths_new:
            continue

        wave_number, task_name = extract_task_wave_and_number(task_path)
        if wave_number not in wave_mapping:
            wave_ids = list(wave_map_name_id.keys())
            print(f'To which wave should the local wave {wave_number} should be assigned? (task {task_name})')
            print('\n'.join(map(lambda x: f"{x[0] + 1}. {wave_map_name_id[x[1]]} (id {x[1]})", enumerate(wave_ids))))
            wave_index = int(input(f'Enter number 1-{len(wave_ids)}: ')) - 1
            wave_mapping[wave_number] = wave_ids[wave_index]
            print(f'Will map {wave_number} to {wave_map_name_id[wave_ids[wave_index]]} ({wave_ids[wave_index]})')
            assert input('OK? y/n ').strip().lower() == 'y', "Ok, bye"

        task = task_path_to_task(repo, task_branch, task_path, wave_mapping)
        print(f'- creating {task_name} ({wave_number})')
        assert create_task(task, *backend), f"could not create task {task}"
        sleep(0.5)

    print('All done')
    return 0


if __name__ == '__main__':
    exit(main())
