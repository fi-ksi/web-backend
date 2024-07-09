import json
import subprocess
from getpass import getpass
from os import environ
from typing import Optional, Tuple
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

    @property
    def backend_url(self) -> str:
        return self.__backend_url

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

    def construct_url(self, path: str) -> Tuple[str, dict]:
        return f"{self.__backend_url}/{path}", {"headers": {'Authorization': self.__token, 'Content-Type': 'application/json'}}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()

    @classmethod
    def load_environment_from_pass(cls, entry: str) -> None:
        # See https://www.passwordstore.org/
        from subprocess import run, PIPE
        try:
            output = run(['pass', 'show', entry], text=True, stdout=PIPE, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return
        for line in output.stdout.splitlines():
            key, value = line.split('=', 1)
            environ[key] = value


    @classmethod
    def login_auto(cls) -> "KSILogin":
        if environ.get('KSI_DISABLE_PASSWORD_STORE') is None:
            cls.load_environment_from_pass(environ.get('KSI_PASSWORD_STORE_ENTRY', 'ksi'))
        username = environ.get('KSI_USERNAME')
        password = environ.get('KSI_PASSWORD')
        backend = environ.get('KSI_BACKEND', 'https://rest.ksi.fi.muni.cz')
        if username is None:
            username = input('Enter your username: ')
        if password is None:
            password = getpass(f'Enter your password for account "{username}": ')

        instance = cls(backend)
        success = instance.login(username, password)
        if not success:
            raise ValueError('Login failed')
        return instance