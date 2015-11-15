import datetime
from sqlalchemy import func, distinct, or_, desc
from sqlalchemy.dialects import mysql

from db import session
import model
import util

def to_json(corr, corr_modules):

	return {
		'id': corr.task.id*100000 + corr.usr.id,
		'task_id': corr.task.id
	}

