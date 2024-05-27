import shutil
import json
from datetime import datetime
from typing import Optional, List, Tuple, TypedDict

import git
import requests

import model
import util
from db import session
from util.task import max_points

LOCKFILE = '/var/lock/ksi-task-new'


def createGit(git_path: str, git_branch: str, author_id: int,
              title: str) -> (str, Optional[int]):
    """
    Vytvori novou ulohu v repozitari a vytvori pull request na GitHubu, pokud je nastaveny token.
    :param git_path: Celá cesta k nové úloze v repozitáři
    :param git_branch: Jméno nové větve
    :param author_id: ID autora úlohy
    :param title: Název úlohy
    :return: SHA commitu a ID pull requestu
    """
    repo = git.Repo(util.git.GIT_SEMINAR_PATH)
    repo.git.checkout("master")
    repo.remotes.origin.pull()

    # Vytvorime novou gitovskou vetev
    repo.git.checkout("HEAD", b=git_branch)

    # Zkopirujeme vzorovou ulohu do adresare s ulohou
    # Cilovy adresar nesmi existovat (to vyzaduje copytree)
    target_path = util.git.GIT_SEMINAR_PATH + git_path
    shutil.copytree(util.git.GIT_SEMINAR_PATH + util.git.TASK_MOOSTER_PATH,
                    target_path)

    # Predzpracovani dat v repozitari
    with open(target_path+'/task.json', 'r') as f:
        data = json.loads(f.read())
    data['author'] = author_id
    with open(target_path+'/task.json', 'w') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))

    with open(target_path+'/assignment.md', 'w') as f:
        s = title + ".\n\n" + \
            "# " + title + "\n\n" + \
            "Název úlohy musí být uvozen `#`, nikoliv podtrhnut rovnítky.\n\n"
        f.write(s)

    # Commit
    repo.index.add([git_path])
    repo.index.commit("Nova uloha: "+title)

    # Push
    # Netusim, jak udelat push -u, tohle je trosku prasarna:
    g = git.Git(util.git.GIT_SEMINAR_PATH)
    g.execute(["git", "push", "-u", "origin", git_branch+':'+git_branch])

    # Pull request
    seminar_repo = util.config.seminar_repo()
    github_token = util.config.github_token()
    github_api_org_url = util.config.github_api_org_url()

    pull_id = None

    if None not in (seminar_repo, github_token, github_api_org_url):
        # PR su per-service, teda treba urobit POST request na GitHub API
        url_root = github_api_org_url + seminar_repo

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + github_token
        }

        pull_id = int(requests.post(
            url_root + "/pulls",
            headers=headers,
            data=json.dumps({
                "title": "Nova uloha: " + title,
                "head": git_branch,
                "base": "master"
            })
        ).json()['number'])

        author: Optional[model.User] = session.query(model.User).\
            filter(model.User.id == int(author_id)).\
            first()

        if author.github:
            requests.post(
                url_root + f"/issues/{pull_id}/assignees",
                headers=headers,
                data=json.dumps({
                    "assignees": [author.github]
                })
            )

    return repo.head.commit.hexsha, pull_id


def fetch_testers(task: model.Task) -> Tuple[List[model.User], List[str]]:
    seminar_repo = util.config.seminar_repo()
    github_token = util.config.github_token()
    github_api_org_url = util.config.github_api_org_url()
    pull_id = task.git_pull_id

    if None in (seminar_repo, github_token, github_api_org_url, pull_id):
        return [], []

    url_root = github_api_org_url + seminar_repo

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "token " + github_token
    }

    response = requests.get(url_root + f"/issues/{pull_id}", headers=headers)
    response.raise_for_status()
    pull_data = response.json()

    reviewer_usernames: List[str] = [reviewer['login'] for reviewer in pull_data.get('requested_reviewers', [])]
    users: List[model.User] = session.query(model.User).filter(model.User.github.in_(reviewer_usernames)).all()
    reviewers_unknown = [reviewer for reviewer in reviewer_usernames if reviewer not in {user.github for user in users}]
    return users, reviewers_unknown

class AdminJson(TypedDict):
    id: int
    title: str
    wave: int
    author: Optional[int]
    co_author: Optional[int]
    testers: List[int]
    git_path: Optional[str]
    git_branch: Optional[str]
    git_commit: Optional[str]
    deploy_date: Optional[datetime]
    deploy_status: str
    max_score: float
    eval_comment: str


def admin_to_json(task: model.Task, amax_points: Optional[float] = None, do_fetch_testers: bool = True)\
        -> AdminJson:
    if not amax_points:
        amax_points = max_points(task.id)

    testers = []
    additional_testers = []

    if do_fetch_testers:
        testers, additional_testers = fetch_testers(task)

    return {
        'id': task.id,
        'title': task.title,
        'wave': task.wave,
        'author': task.author,
        'co_author': task.co_author,
        'git_path': task.git_path,
        'git_branch': task.git_branch,
        'git_commit': task.git_commit,
        'deploy_date':
            task.deploy_date.isoformat() if task.deploy_date else None,
        'deploy_status': task.deploy_status,
        'max_score': float(format(amax_points, '.1f')),
        'eval_comment': task.eval_comment,
        'testers': testers,
        'additional_testers': additional_testers
    }
