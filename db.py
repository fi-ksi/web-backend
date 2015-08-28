import sqlalchemy
from sqlalchemy.orm import sessionmaker

import config

engine = sqlalchemy.create_engine(config.SQL_ALCHEMY_URI)
_session = sessionmaker(bind=engine)
session = _session()
