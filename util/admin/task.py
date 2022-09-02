import shutil
import json
from typing import Optional

import git
import requests

import model
import util
from db import session

LOCKFILE = '/var/lock/ksi-task-new'


def createGit(git_path, git_branch, author_id, title):
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

    if None not in (seminar_repo, github_token):
        # PR su per-service, teda treba urobit POST request na GitHub API
        url_root = "https://api.github.com/repos/fi-naskoc/" + util.config.seminar_repo()

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + util.config.github_token()
        }

        pull_id = requests.post(
            url_root + "/pulls",
            headers=headers,
            data=json.dumps({
                "title": "Nova uloha: " + title,
                "head": git_branch,
                "base": "master"
            })
        ).json()['number']

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

    return repo.head.commit.hexsha
