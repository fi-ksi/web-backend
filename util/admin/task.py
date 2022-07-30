import shutil
import json
import git
import requests
import config

import util

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
    # PR su per-service, teda treba urobit POST request na GitHub API
    url = "https://api.github.com/repos/fi-ksi/" + config.seminar_repo() + "/pulls"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "token" + config.github_token(),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = "{'title': 'Nova uloha: " + title + "'," + \
        "'head': '" + git_branch + "'," + \
        "'base': 'master'}"

    requests.post(url, headers=headers, data=data)

    return repo.head.commit.hexsha
