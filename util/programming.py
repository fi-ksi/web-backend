from db import session
import model

def build(module_id):
	programming = session.query(model.Programming).filter(model.Programming.module == module_id).first()

	return programming.default_code