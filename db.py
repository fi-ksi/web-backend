import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.interfaces import ConnectionProxy
import sys

import config


# When `proxy=MyProxy()` is added to create_angine parameters
# this proxy shows mysql requests. This could be used to
# measure amount of SQL requests.
class MyProxy(ConnectionProxy):
    def cursor_execute(self, execute, cursor, statement, parameters, context,
                       executemany):
        print("EXECUTING " + statement[:70] + str(parameters))
        sys.stdout.flush()
        return execute(cursor, statement, parameters, context)


engine = sqlalchemy.create_engine(config.SQL_ALCHEMY_URI,
                                  isolation_level="READ COMMITTED",
                                  pool_recycle=3600)
_session = sessionmaker(bind=engine)
session = _session()
