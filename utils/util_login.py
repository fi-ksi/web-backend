import json
from getpass import getpass
from typing import Optional
from urllib import request
from urllib.error import HTTPError
from urllib.parse import urlencode


class KSILogin:
    def __init__(self, backend_url: str) -> None:
        self.__backend_url: str = backend_url
        self.__token: Optional[str] = None

    def __del__(self) -> None:
        self.logout()

    @property
    def token(self) -> str:
        if self.__token is None:
            raise ValueError('User not logged in yet, token is None')
        return self.__token

    def logout(self) -> None:
        if self.__token is None:
            return
        with request.urlopen(request.Request(f"{self.__backend_url}/logout", headers={'Authorization': self.__token})) as res:
            res.read()

    def login(self, username: str, password: Optional[str] = None) -> bool:
        if self.__token is not None:
            return True

        if password is None:
            password = getpass(f'Enter you password for account "{username}": ')

        req = request.Request(
            f"{self.__backend_url}/auth",
            method="POST",
            data=urlencode({
                'username': username,
                'password': password,
                'grant_type': 'password',
                'refresh_token': ''
            }).encode('utf8')
        )
        try:
            with request.urlopen(req) as res:
                # TODO: save and handle refresh token
                data = json.loads(res.read().decode('utf8'))
                self.__token = data['token_type'] + ' ' + data['access_token']
            return True
        except HTTPError:
            return False
