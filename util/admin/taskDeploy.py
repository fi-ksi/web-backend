from db import session
from lockfile import LockFile
import model
import json
import time

# Deploy muze byt jen jediny na cely server -> pouzivame lockfile.
LOCKFILE = '/var/lock/ksi-task-deploy'

# Deploy je spousten v samostatnem vlakne.

def deploy(task, deployLock):
	# TODO: magic
	# 1) git checkout task.git_branch
	# 2) git pull
	# 3) convert data to DB
	# 4) task.git_commit = last_commit_hash

	time.sleep(20)

	deployLock.release()

