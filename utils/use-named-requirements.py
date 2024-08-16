#!/usr/bin/env python3

"""
Replaces all ID-based prerequisities with their name-based alternatives by resolving their IDs againts the backend

The first argument may be path to the task.json file or to a directory in which the task.json is supposed to be recursivelly searched
"""

from urllib import request
from pathlib import Path
from typing import Set, NamedTuple, Dict
from os import environ
from sys import argv
import json
import re

from util_login import KSILogin


def fetch_task_path(task_id: int, backend_url: str, token: str) -> str:
    """
    Fetches git path for given task
    :param backend_url: url of the backend, including https
    :param token: login token
    :param task_id: ID of the task to fetch
    :return: git path of given task
    """
    with request.urlopen(request.Request(f"{backend_url}/admin/atasks/{task_id}", headers={'Authorization': token})) as res:
        result = json.loads(res.read().decode('utf8'))
    return result["atask"]["git_path"]


def replace_requiements(file_task_meta: Path, backend_url: str, token: str) -> None:
    print(f"[*] processing {file_task_meta.absolute()}")

    with file_task_meta.open('r') as f:
        content = json.load(f)

    requirements = content["prerequisities"]
    print(f"  [-] {requirements=}")
    if requirements is None:
        return
    # force string for int-based requiements
    requirements = str(requirements)

    def _replace(match: re.Match):
        prefix = match.group(1)
        suffix = match.group(3)
        task_id = int(match.group(2))
        print(f"    [.] processing {task_id} ... ", end="", flush=True)
        task_path = fetch_task_path(task_id, backend_url, token).rsplit('/', 1)[-1]
        print(task_path)
        return f"{prefix}{task_path}{suffix}"

    requirements = re.sub(r"(^|\s)(\d+)($|\s)", _replace, requirements)
    print(f"  [-] {requirements=}")
    content["prerequisities"] = requirements

    with file_task_meta.open('w') as f:
        json.dump(content, f, indent=4)


def main() -> int:
    login = KSILogin.login_auto()

    backend = (login.backend_url, login.token)

    source = Path(argv[1])
    if source.is_file():
        replace_requiements(source, *backend)
    else:
        for task_meta in source.rglob("task.json"):
            replace_requiements(task_meta, *backend)


if __name__ == '__main__':
    exit(main())
