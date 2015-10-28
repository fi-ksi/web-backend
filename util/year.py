import os
from sqlalchemy import func, desc

from db import session
import model
import util

def get_year(year = None):
	if year is None:
	        tasks = session.query(func.max(model.Year))
	else:
		return year


