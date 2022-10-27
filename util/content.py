import os
from typing import List, TypedDict


class Content(TypedDict):
    id: str
    files: List[str]
    dirs: List[str]


def empty_content(path: str) -> Content:
    return {'id': path, 'files': [], 'dirs': []}


def dir_to_json(path: str) -> Content:
    path_full = os.path.join('data', 'content', path)

    if os.path.isdir(path_full):
        return {
            'id': path,
            'files': [f for f in os.listdir(path_full)
                      if os.path.isfile(path_full+'/'+f)],
            'dirs':  [f for f in os.listdir(path_full)
                      if os.path.isdir(path_full+'/'+f)]
        }
    else:
        return empty_content(path)
