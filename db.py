import sqlalchemy
from enum import Enum
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

import config


class DBMode(Enum):
    SQLITE = "sqlite"
    MYSQL = "mysql"


db_mode: DBMode = DBMode.SQLITE if config.SQL_ALCHEMY_URI.lower().startswith("sqlite") else DBMode.MYSQL


def __set_sql_mode(_conn, *_):
    if db_mode == DBMode.MYSQL:
        # ONLY_FULL_GROUP_BY is not compatible with some queries in the application, disable it
        _conn.cursor().execute("SET sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));")


engine = sqlalchemy.create_engine(config.SQL_ALCHEMY_URI,
                                  isolation_level="READ COMMITTED" if db_mode == DBMode.MYSQL else "SERIALIZABLE",
                                  connect_args={} if db_mode == DBMode.MYSQL else {"check_same_thread": False},
                                  pool_recycle=3600)
event.listen(engine, "connect", __set_sql_mode)
_session = sessionmaker(bind=engine)
session = _session()
