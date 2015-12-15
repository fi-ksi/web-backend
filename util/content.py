import os

def dir_to_json(path):
	return {
		'id': path,
		'files': [ f for f in os.listdir(path) if os.path.isfile(path+'/'+f) ],
		'dirs':  [ f for f in os.listdir(path) if os.path.isdir(path+'/'+f) ]
	}

