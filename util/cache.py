from datetime import datetime, timedelta
from typing import Optional
from gzip import compress, decompress
from pickle import dumps, loads
from base64 import b64encode, b64decode

from db import session
from model.cache import Cache


def get_key(user: Optional[int], role: Optional[str], year: Optional[int], subkey: str) -> str:
    """
    Get a key for a user or role
    :param user: user ID
    :param role: role name
    :param subkey: key name
    :param year: year
    :return: key name
    """
    year = int(year) if year is not None else None
    user = int(user) if user is not None else None
    return f"{user=}:{role=}:{year=}:{subkey=}"


def get_record(key: str) -> Optional[any]:
    """
    Get a record from cache
    :param key: key to get
    :return: data
    """
    data = session.query(Cache).filter(Cache.key == key).first()
    if data is None:
        return None
    if datetime.now() > data.expires:
        invalidate_cache(key)
        return None
    return loads(decompress(b64decode(data.value.encode('ascii'))))


def invalidate_cache(key: str) -> None:
    """
    Invalidate cache
    :param key: key to invalidate
    """
    session.query(Cache).filter(Cache.key == key).delete()
    session.commit()


def save_cache(key: str, data: any, expires_second: int) -> None:
    """
    Save data to cache
    :param expires_second: seconds until record is considered expired
    :param key: key to save
    :param data: data to save
    """
    data = b64encode(compress(dumps(data))).decode('ascii')

    if get_record(key) is not None:
        session.query(Cache).filter(Cache.key == key).delete()
    expires = datetime.now() + timedelta(seconds=expires_second)
    session.add(Cache(key=key, value=data, expires=expires))
    session.commit()
