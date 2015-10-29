import sqlalchemy
from sqlalchemy.orm import sessionmaker

import config

engine = sqlalchemy.create_engine(config.SQL_ALCHEMY_URI, isolation_level="READ COMMITTED", pool_recycle=-1)
_session = sessionmaker(bind=engine)
session = _session()
