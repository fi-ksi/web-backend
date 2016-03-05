# -*- coding: utf-8 -*-

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DisconnectionError

import config

def checkout_listener(dbapi_con, con_record, con_proxy):
	try:
		try:
			dbapi_con.ping(False)
		except TypeError:
			dbapi_con.ping()
	except dbapi_con.OperationalError as exc:
		if exc.args[0] in (2006, 2013, 2014, 2045, 2055):
			raise DisconnectionError()
		else:
			raise

engine = sqlalchemy.create_engine(config.SQL_ALCHEMY_URI, isolation_level="READ COMMITTED", pool_recycle=3600)
sqlalchemy.event.listen(engine, 'checkout', checkout_listener)
_session = sessionmaker(bind=engine)
session = _session()

