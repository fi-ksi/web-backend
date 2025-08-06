import sqlalchemy
from enum import Enum
from sqlalchemy.orm import sessionmaker

import config


class DBMode(Enum):
    SQLITE = "sqlite"
    MYSQL = "mysql"


db_mode: DBMode = DBMode.SQLITE if config.SQL_ALCHEMY_URI.lower().startswith("sqlite") else DBMode.MYSQL

engine = sqlalchemy.create_engine(config.SQL_ALCHEMY_URI,
                                  isolation_level="READ COMMITTED" if db_mode == DBMode.MYSQL else "SERIALIZABLE",
                                  connect_args={} if db_mode == DBMode.MYSQL else {"check_same_thread": False},
                                  pool_recycle=3600)
_session = sessionmaker(bind=engine)
session = _session()
