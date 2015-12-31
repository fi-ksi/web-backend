import util, git

LOCKFILE = '/var/lock/ksi-task-new'

def createGit(git_path, git_branch, author, title):
	# DEBUG
	return None

	repo = git.Repo(util.git.GIT_SEMINAR_PATH)
	repo.remotes.origin.pull()

	new_branch = repo.create_head(git_branch)

	# TODO


