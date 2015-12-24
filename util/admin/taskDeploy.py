# -*- coding: utf-8 -*-

from db import session
from lockfile import LockFile
import model
import json
import time
import pypandoc
import re
import os
import shutil

# Deploy muze byt jen jediny na cely server -> pouzivame lockfile.
LOCKFILE = '/var/lock/ksi-task-deploy'

# Deploy je spousten v samostatnem vlakne.

def deploy(task, deployLock):
	# TODO: magic
	# 0) git check_if_exists task.git_branch
	# 1) git checkout task.git_branch
	# 2) git pull
	# 3) git check_if_exists task.git_path
	# 4) convert data to DB
	# 5) task.git_commit = last_commit_hash

	try:
		time.sleep(20)
	except:
		raise
	finally:
		deployLock.release()

###############################################################################
# Parsovani dat z repozitare:

def process_meta(task, filename):
	with open(filename, 'r') as f:
		data = json.loads(f)

	task.author = data['author']
	task.time_deadline = data['time_deadline']
	if ('icon_ref' in data) and (data['icon_ref'] is not None):
		task.picture_base = 'data/task-content/' + str(task.id) + '/icon/'
	else:
		task.picture_base = None

	# TODO: prerequisities

# Vlozi zadani ulohy do databaze
def process_assignment(task, filename):
	with open(filename, 'r') as f: data = f.read()
	data = ksi_pseudocode(data)
	data = ksi_collapse(data)
	parsed = parse_pandoc(data).splitlines()

	# Intro ulohy
	intro = re.search("<p>(.*?)</p>", parsed[0])
	if intro is not None:
		task.intro = intro.group(1)
		parsed.pop(0)
	else:
		task.intro = ""

	# Nadpis ulohy
	title = re.search("<h1>(.*?)</h1>", parsed[0])
	if title is not None:
		task.title = title.group(1)
		parsed.pop(0)

	# Seznam radku spojime na jeden dlouhy text
	body = '\n'.join(parsed)
	body = replace_h(body)
	body = change_links(task, body)
	task.body = body

# Vlozi reseni ulohy do databaze
def process_solution(task, filename):
	if os.path.isfile(filename):
		with open(filename, 'r') as f: data = f.read()
		data = ksi_pseudocode(data)
		data = ksi_collapse(data)
		task.solution = change_links(task, replace_h(parse_pandoc(data)))
	else:
		task.solution = None

# Zkopiruje ikony z gitovskeho adresare do adresare backendu
def process_icons(task, source_path):
	target_path = "data/task-content/" + str(task.id) + "/icon/"
	files = [ "base.svg", "correcting.svg", "locked.svg", "done.svg" ]
	for f in files:
		if os.path.isfile(source_path+"/"+f):
			shutil.copy2(source_path+"/"+f, target_path+f)

# Zkopiruje veskera data do adresare dat backendu
def process_data(task, source_path):
	target_path = "data/task-content/" + str(task.id) + "/zadani/"
	shutil.copytree(source_path, target_path)

def process_modules(task, git_path):
	# Aktualni moduly v databazi
	modules = session.query(model.Module).\
		filter(model.Module.task == task.id).\
		order_by(model.Module.order).all()

	i = 1
	while (os.path.isdir(git_path+"/module"+str(i))):
		if modules[i]:
			module = modules[i]
		else:
			module = model.Module(
				task = task.id,
				type = "general",
				name = "",
				order = i
			)
		process_module(module, git_path+"/module"+str(i))

		try:
			if not modules[i]: session.add(module)
			session.commit()
		except:
			session.rollback()
			raise

		i += 1

# Zpracovani modulu
# \module je vzdy inicializovany
# \module_path muze byt bez lomitka na konci
def process_module(module, module_path):
	process_module_json(module, module_path+"/module.json")
	# TODO: parse module.md

# Zpracovani souboru module.json
def process_module_json(module, filename):
	with open(filename, 'r') as f:
		data = json.loads(f)
	module.type = data['type'],
	module.max_points = data['max_points']
	module.autocorrect = data['autocorrect']
	module.bonus = data['bonus'] if 'bonus' in data else False
	module.action = data['action'] if 'action' in data else ""
	# TODO: parse programming

###############################################################################
# Pomocne parsovaci funkce:

# Parsovani stringu \source pandocem
def parse_pandoc(source):
	return pypandoc.convert(source, 'html5', format='md', extra_args=['--smart', '--mathjax'])

# <h2> -> <h3>, <h3> -> <h4>, <h4> -> <h5> (to musi stacit)
def replace_h(source):
	return body.replace("<h2>", "<h3>").replace("</h2>", "</h3>"). \
		replace("<h3>", "<h4>").replace("</h3>", "</h4>"). \
		replace("<h4>", "<h5>").replace("</h4>", "</h5>")

# Nahrazuje <ksi-pseudocode> za prislusne HTML
def ksi_pseudocode(source):
	source = re.sub(ur"(<ksi-pseudocode>.*)(function|procedure|Vstup|Výstup|if|then|return|else|fi)(.*</ksi-pseudocode>)", r"\1**\2**\3", source)
	source = re.sub(r"<ksi-pseudocode>", r"<div style=\"padding-left:20px\">", source)
	source = re.sub(r"</ksi-pseudocode>", r"</div>", source)
	return source

# Nahrazuje <ksi-collapse> za HTML plne silenych <div>u
def ksi_collapse(source):
	source = re.sub(r"<ksi-pseudocode title=\"(.*?)\">", lambda m, i=iter(int, 1): r"""
		<div class="panel panel-ksi panel-group">
		<div class="panel-heading panel-heading-ksi"><h4 class="panel-title"><a data-toggle="collapse" href="#collapse""" + str(next(i)) + """">""" + m.group(1) + """</a></h4></div>
		<div id="collapse""" + str(next(i)-1) + """" class="panel-collapse collapse">
		<div class="panel-body">""", source)
	return source.replace("</ksi-collapse>", "</div></div></div>")

# Nahrazuje odkazy do data/ za odkazy do backendu
def change_links(task, source):
	return re.sub(r"\"data/", r"\""+util.config.ksi_web()+"/task-content/"+str(task.id)+"/", source)

###############################################################################

