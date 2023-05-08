#!/usr/bin/env/python3

"""
Parses seminar repository and asks if it should create all found tasks that are not currently found on backend.
Requires following environment variables:
- REPO - path to the seminar repository
- YEAR - the year/directory name inside seminar repository
- BACKEND - backend URL including https
- TOKEN - your login token (can be extracted from frontend)
"""

import re
import json
from urllib import request
from pathlib import Path
from subprocess import check_output
from typing import Set, NamedTuple, Dict
from os import environ


class MockKSITask(NamedTuple):
    title: str
    wave_id: int
    author: int
    git_path: str
    git_branch: str

def task_path_to_task(repo: Path, branch: str, task_path: str, waves: Dict[int, int]) -> MockKSITask:
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


def extract_task_wave_and_number(task_path: str) -> (int, str):
    """
    Extracts task name and wave number from the path root
    :param task_path: path inside git
    :return: task wave index and task name
    """
    re_task_meta = re.compile(r'^\d+/vlna(\d+)/uloha_\d+_(.+)$')
    match = re_task_meta.match(task_path)
    assert match is not None, f"Invalid task root ({task_path})"
    wave_number = int(match.group(1))
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
    re_task_path = re.compile(r'^(\d+/vlna\d+/uloha_\d+_.+?)/')
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
        for path in extract_task_paths(repo, branch):
            if not path.startswith(filter_year):
                continue
            data[path] = branch

    return data

def main() -> int:
    backend = (environ['BACKEND'], environ['TOKEN'])
    repo = Path(environ['REPO'])
    tasks_all = extrack_task_paths_all(repo, environ['YEAR'])

    paths_known = fetch_known_paths(*backend)

    paths_new = tasks_all.keys() - paths_known
    print(f'Found {len(paths_new)} new tasks:')
    print('\n'.join(paths_new))
    print()
    assert input('OK? y/n ').strip().lower() == 'y', "Ok, bye"

    wave_map_name_id = fetch_known_waves(*backend)

    wave_mapping: Dict[int, int] = {}

    for task_path, task_branch in tasks_all.items():
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

    print('All done')
    return 0


if __name__ == '__main__':
    exit(main())
