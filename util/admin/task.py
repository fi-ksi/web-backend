import util, git, shutil, os, json

LOCKFILE = '/var/lock/ksi-task-new'

def createGit(git_path, git_branch, author_id, title):
	print "Initing repo"
	repo = git.Repo(util.git.GIT_SEMINAR_PATH)
	repo.remotes.origin.pull()
	repo.git.checkout("master")

	# Vytvorime novou gitovskou vetev
	print "Creating new branch", git_branch
	repo.git.checkout("HEAD", b=git_branch)

	# Zkopirujeme vzorovou ulohy do adresare s ulohou
	target_path = util.git.GIT_SEMINAR_PATH + git_path
	print "Copying mooster to", target_path

	shutil.copytree(util.git.GIT_SEMINAR_PATH + util.git.TASK_MOOSTER_PATH, target_path)

	# Predzpracovani dat v repozitari
	with open(target_path+'/task.json', 'r') as f:
		data = json.loads(f.read())
	data['author'] = author_id
	data['prerequisities'] = None
	with open(target_path+'/task.json', 'w') as f:
		f.write(json.dumps(data, indent=4))

	# Vytvorime commit
	print "Creating commit..."
	repo.index.add([ git_path ])
	repo.index.commit("Nova uloha: "+title)

	#repo.remotes.origin.push({ "-u":"" })

	print "Done"
