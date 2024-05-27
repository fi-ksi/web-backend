#!/usr/bin/env/python3

"""
Parses seminar repository and asks if it should create all found tasks that are not currently found on backend.
Optionally set following environment variables:
- YEAR - the year/directory name inside seminar repository
- BACKEND - backend URL including https
- TOKEN - your login token (can be extracted from frontend)
"""
import collections
import json
from typing import Dict, TypedDict, Optional, List, Set
from urllib import request

from util_login import KSILogin


class Task(TypedDict):
    id: int
    title: str
    wave: int
    max_score: float
    author: int
    co_author: Optional[int]
    testers: List[int]
    additional_testers: List[str]
    git_pull_id: Optional[int]


class Wave(TypedDict):
    id: int
    caption: str
    garant: int


# noinspection PyDefaultArgument
def fetch_user_name(backend: KSILogin, user_id: int, cache: Dict[int, str] = {}) -> str:
    if user_id not in cache:
        url, params = backend.construct_url(f'/users/{user_id}')
        with request.urlopen(request.Request(url, **params)) as res:
            user = json.loads(res.read().decode('utf8'))['user']
        cache[user_id] = f"{user['first_name'].strip()} {user['last_name'].strip()} ({user_id})"
    return cache[user_id]


def fetch_known_waves(backend: KSILogin) -> Dict[int, Wave]:
    url, params = backend.construct_url('/waves')
    with request.urlopen(request.Request(url, **params)) as res:
        waves = json.loads(res.read().decode('utf8'))['waves']
    return {x['id']: x for x in waves}



def fetch_known_tasks(backend: KSILogin) -> List[Task]:
    url, params = backend.construct_url('/admin/atasks?fetch_testers=1')
    with request.urlopen(request.Request(url, **params)) as res:
        waves = json.loads(res.read().decode('utf8'))['atasks']
    return waves


def main() -> int:
    user_lines: Dict[str, List[str]] = collections.defaultdict(list)
    unknown_testers: Set[str] = set()
    unmatched_tasks: Set[str] = set()

    with KSILogin.login_auto() as login:
        waves = fetch_known_waves(login)

        print('Select the minimal wave number to be included in the report:')
        for wave_id, wave_data in waves.items():
            print(f"{wave_id}: {wave_data['caption']} (garant: {fetch_user_name(login, wave_data['garant'])})")
        min_wave = int(input('Enter the minimal wave number: '))
        assert min_wave in waves

        for wave_id, wave_data in waves.items():
            if wave_id < min_wave:
                continue
            user_lines[fetch_user_name(login, wave_data['garant'])].append(f"G{wave_id}")

        for task in fetch_known_tasks(login):
            task_author: str = fetch_user_name(login, task["author"])
            task_co_author: Optional[str] = fetch_user_name(login, task["co_author"]) if task["co_author"] else None
            testers: List[str] = [fetch_user_name(login, tester) for tester in task["testers"]] + task["additional_testers"]
            task_is_large: bool = task["max_score"] > 5.0
            wave: int = task["wave"]

            if wave < min_wave:
                continue

            unknown_testers.update(task["additional_testers"])
            if task["git_pull_id"] is None:
                unmatched_tasks.add(f"{task['title']} (wave {wave}, id {task['id']})")
                continue

            author_line = f"{'U' if task_is_large else 'u'}{wave}" + ('' if task_co_author is None else '_')
            tester_line = f"{'T' if task_is_large else 't'}{wave}"

            user_lines[task_author].append(author_line)
            if task_co_author:
                user_lines[task_co_author].append(author_line)

            for tester in testers:
                if tester == fetch_user_name(login, waves[wave]['garant']):
                    continue
                user_lines[tester].append(tester_line)

    print('ORGANIZATION PERFORMANCE REPORT')
    for user, line_parts in user_lines.items():
        line_parts_with_count = []
        for distinct_part in set(line_parts):
            line_parts_with_count.append(f"{line_parts.count(distinct_part) if not distinct_part.startswith('G') else ''}{distinct_part}")
        print(f"{user}: {'; '.join(line_parts_with_count)}")

    if unknown_testers or unmatched_tasks:
        print('WARNING: SOME ENTRIES COULD NOT BE MATCHED')
        if unknown_testers:
            print("Unknown testers:\n- " + '\n- '.join(unknown_testers))
        if unmatched_tasks:
            print("Unmatched tasks:\n- " + '\n- '.join(unmatched_tasks))

    return 0


if __name__ == '__main__':
    exit(main())
