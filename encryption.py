from ssage import SSAGE
from ssage.backend import SSAGEBackendAge

from config import ENCRYPTION_KEY


def get_encryptor() -> SSAGE:
    """
    Get an encryptor object
    :return: SSAGE object
    """
    return SSAGE(ENCRYPTION_KEY, authenticate=False, strip=False, backend=SSAGEBackendAge)


def encrypt(data: str) -> str:
    """
    Encrypt data using AGE encryption
    :param data: data to encrypt
    :return: ASCII armored encrypted data
    """
    return get_encryptor().encrypt(data)


def decrypt(data: str) -> str:
    """
    Decrypt data using AGE encryption
    :param data: ASCII armored encrypted data
    :return: decrypted data
    """
    return get_encryptor().decrypt(data)
