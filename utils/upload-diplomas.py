#!/usr/bin/env/python3

"""
Parses seminar repository and asks if it should create all found tasks that are not currently found on backend.
Requires following environment variables:
- DIPLOMAS - path to the directory with signed diploma PDFs
- YEAR_ID - id of the year to get users from
- BACKEND - backend URL including https
- TOKEN - your login token (can be extracted from frontend)
"""
import json
from os import environ
from pathlib import Path
from typing import Dict, Set, Union
from urllib import request
from util_login import KSILogin


def fetch_successful_user_diplomas(user_id: int, backend_url: str, token: str, year: Union[str, int]) -> Set[int]:
    """
    Fetches years for which user was given a diploma
    :param backend_url: url of the backend, including https
    :param token: login token
    :param year: year id
    :param user_id: id of the user
    :return: years for which user was given a diploma
    """
    with request.urlopen(request.Request(f"{backend_url}/diplomas/{user_id}", headers={'Authorization': token, 'year': year})) as res:
        diplomas = json.loads(res.read().decode('utf8'))['diplomas']

    return set(map(
        lambda x: x['year'],
        diplomas
    ))


def fetch_successful_users(backend_url: str, token: str, year: Union[str, int]) -> Dict[str, int]:
    """
    Fetches a map of all SUCCESSFUL users in the year in format email: user_id
    :param backend_url: url of the backend, including https
    :param token: login token
    :param year: year id
    :return: users map in format email: user_id
    """
    with request.urlopen(request.Request(f"{backend_url}/users", headers={'Authorization': token, 'year': year})) as res:
        users = json.loads(res.read().decode('utf8'))['users']

    return {
        u['email']: u['id']
        for u in filter(
            lambda x: x.get('successful', False),
            users
        )
    }


def upload_diploma(user_id: int, diploma: Path, backend_url: str, token: str, year: Union[str, int]) -> None:
    with diploma.open('rb') as f:
        diploma_content = f.read()

    data_boundary = b'ksi12345678ksi'
    data = b'--' + data_boundary + b'\n' + \
           b'Content-Disposition: form-data; name="file" filename="diploma.pdf"\n' + \
           b'Content-Type: application/pdf\n\n' + \
           diploma_content + b'\n\n' + \
           b'--' + data_boundary + b'--'

    req = request.Request(
        f"{backend_url}/admin/diploma/{user_id}/grant",
        headers={
            'Authorization': token,
            'year': year,
            'Content-Type': 'multipart/form-data; charset=UTF-8; boundary=' + data_boundary.decode('ascii'),
            'Content-Length': len(data)
        },
        method="POST",
        data=data
    )

    with request.urlopen(req) as res:
        res.read()

def main() -> int:
    backend_url = environ['BACKEND']
    year_id = int(environ['YEAR_ID'])

    if 'TOKEN' not in environ:
        login = KSILogin(backend_url)
        if not login.login(environ['USER'], environ.get('PASSWORD')):
            print('ERROR: Login failed')
            return 1
        environ['TOKEN'] = login.token

    backend = (backend_url, environ['TOKEN'], year_id)
    dir_diplomas = Path(environ['DIPLOMAS'])

    if not dir_diplomas.is_dir():
        print(f'{dir_diplomas} is not valid directory')

    user_map = fetch_successful_users(*backend)
    print(f"Found {len(user_map)} successful users")

    pdf_diploma_extension = '.signed.pdf'
    files_diplomas = [x for x in dir_diplomas.iterdir() if x.name.lower().endswith(pdf_diploma_extension)]
    print(f"Found {len(files_diplomas)} diplomas")

    emails_left: Set[str] = set(user_map.keys())
    emails_extra: Set[str] = set()
    for file_diploma in files_diplomas:
        email = file_diploma.name.split(pdf_diploma_extension, 1)[0]
        if email not in user_map:
            emails_extra.add(email)
            continue
        emails_left.remove(email)
        if year_id in fetch_successful_user_diplomas(user_map[email], *backend):
            print(f'- {email} already has a diploma for this year')
            continue
        print(f'- uploading diploma for {email}')
        upload_diploma(user_map[email], file_diploma, *backend)

    if emails_left:
        print(f"Users without diploma: {emails_left}")
    else:
        print('All diplomas found')
    if emails_extra:
        print(f"Users that should not have diploma: {emails_extra}")
    else:
        print('No extra diplomas found')
    return 0


if __name__ == '__main__':
    exit(main())
