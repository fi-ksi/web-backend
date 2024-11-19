import os
from typing import List, TypedDict, Union
from pathlib import Path

from util.logger import audit_log


class Content(TypedDict):
    id: str
    files: List[str]
    dirs: List[str]


def empty_content(path: str) -> Content:
    return {'id': path, 'files': [], 'dirs': []}


def dir_to_json(path: Union[str, Path]) -> Content:
    path_base = Path('data', 'content').absolute()
    path_full = (path_base / path).absolute() if isinstance(path, str) or not path.is_absolute() else path

    if not path_full.is_relative_to(path_base):
        audit_log(
            scope="HACK",
            user_id=None,
            message=f"Attempt to access content outside box using dir_to_json",
            message_meta={
                'path': path
            }
        )
        return empty_content(path)

    if os.path.isdir(path_full):
        return {
            'id': str(path_full.relative_to(path_base)),
            'files': [f for f in os.listdir(path_full)
                      if (path_full / f).is_file()],
            'dirs':  [f for f in os.listdir(path_full)
                      if (path_full / f).is_dir()]
        }
    else:
        return empty_content(path)
