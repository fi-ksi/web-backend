from lockfile import LockFile
import util

GIT_LOCKS = [
	util.admin.taskDeploy.LOCKFILE,
	util.admin.waveDiff.LOCKFILE
]

def git_locked():
	for lock in GIT_LOCKS:
		if LockFile(lock).is_locked():
			return lock
	return None

