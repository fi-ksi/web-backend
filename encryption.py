from io import BytesIO

from age.cli import encrypt as age_encrypt, Decryptor as AgeDecryptor, AsciiArmoredInput, AGE_PEM_LABEL
from age.keys.agekey import AgePrivateKey

from config import ENCRYPTION_KEY


def __age_key() -> AgePrivateKey:
    """
    Get AGE private key
    :return: AGE private key
    """
    return AgePrivateKey.from_private_string(ENCRYPTION_KEY)


class __CaptureOnClose(BytesIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__captured_data = None

    def close(self):
        self.__captured_data = self.getvalue()
        super().close()

    @property
    def captured_data(self):
        if not self.closed:
            return self.getvalue()

        data = self.__captured_data
        self.__captured_data = None
        return data


def encrypt_bytes(data: bytes) -> str:
    """
    Encrypt data using AGE encryption
    :param data: data to encrypt
    :return: ASCII armored encrypted data
    """
    key_public = __age_key().public_key()
    data_in = BytesIO(data)
    data_out = __CaptureOnClose()

    age_encrypt(
        recipients=[key_public.public_string()],
        infile=data_in,
        outfile=data_out,
        ascii_armored=True
    )

    return data_out.captured_data.decode('ascii')


def decrypt_bytes(data: str) -> bytes:
    """
    Decrypt data using AGE encryption
    :param data: ASCII armored encrypted data
    :return: decrypted data
    """
    key = __age_key()
    data_in = AsciiArmoredInput(AGE_PEM_LABEL, BytesIO(data.encode('ascii')))
    data_out = __CaptureOnClose()

    with AgeDecryptor([key], data_in) as decryptor:
        data_out.write(decryptor.read())

    return data_out.captured_data


def encrypt(data: str) -> str:
    """
    Encrypt data using AGE encryption
    :param data: data to encrypt
    :return: ASCII armored encrypted data
    """
    return encrypt_bytes(data.encode('utf-8'))


def decrypt(data: str) -> str:
    """
    Decrypt data using AGE encryption
    :param data: ASCII armored encrypted data
    :return: decrypted data
    """
    return decrypt_bytes(data).decode('utf-8')
