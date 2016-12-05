# -*- coding: utf-8 -*-

import os

def empty_content(path):
    return { 'id': path, 'files': [], 'dirs': [] }

def dir_to_json(path):
    path_full = 'data/content/'+path

    if os.path.isdir(path_full):
        return {
            'id': path,
            'files': [ f for f in os.listdir(path_full) if os.path.isfile(path_full+'/'+f) ],
            'dirs':  [ f for f in os.listdir(path_full) if os.path.isdir(path_full+'/'+f) ]
        }
    else:
        return empty_content(path)

