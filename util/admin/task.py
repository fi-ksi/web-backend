import util, git, shutil, os, json

LOCKFILE = '/var/lock/ksi-task-new'

def createGit(git_path, git_branch, author_id, title):
	repo = git.Repo(util.git.GIT_SEMINAR_PATH)
	repo.git.checkout("master")
	repo.remotes.origin.pull()

	# Vytvorime novou gitovskou vetev
	repo.git.checkout("HEAD", b=git_branch)

	# Zkopirujeme vzorovou ulohy do adresare s ulohou
	# Cilovy adresar nesmi existovat (to vyzaduje copytree)
	target_path = util.git.GIT_SEMINAR_PATH + git_path
	shutil.copytree(util.git.GIT_SEMINAR_PATH + util.git.TASK_MOOSTER_PATH, target_path)

	# Predzpracovani dat v repozitari
	with open(target_path+'/task.json', 'r') as f:
		data = json.loads(f.read())
	data['author'] = author_id
	data['prerequisities'] = None
	with open(target_path+'/task.json', 'w') as f:
		f.write(json.dumps(data, indent=4))

	# Commit
	repo.index.add([ git_path ])
	repo.index.commit("Nova uloha: "+title)

	# Push
	# Netusim, jak udelat push -u, tohle je trosku prasarna:
	g = git.Git(util.git.GIT_SEMINAR_PATH)
	g.execute(["git", "push", "-u", "origin", git_branch+':'+git_branch])

