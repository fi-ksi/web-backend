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
		task.intro = "Intro ulohy nenalezeno"

	# Nadpis ulohy
	title = re.search("<h1(.*?)>(.*?)</h1>", parsed[0])
	if title is not None:
		task.title = title.group(2)
		parsed.pop(0)
	else:
		task.title = "Nazev ulohy nenalezen"

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
			session.add(module)

		process_module(module, git_path+"/module"+str(i))

		try:
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
	process_module_md(module, module_path+"/module.md")

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

# Zpracovani module.md
# Pandoc spoustime az uplne nakonec, abychom mohli provest analyzu souboru.
def process_module_md(module, filename):
	with open(filename, 'r') as f:
		data = f.readlines()

	# Hledame nazev modulu na nultem radku
	name = re.search(r"# (.*?)", data[0])
	if name is not None:
		module.name = re.search(r"<h1(.*?)>(.*?)</h1>", parse_pandoc(name.group(1))).group(2)
		parsed.pop(0)
	else:
		module.name = "Nazev modulu nenalezen"

	# Ukolem nasledujicich metod je zpracovat logiku modulu a v \data zanechat uvodni text
	if module.type == model.ModuleType.GENERAL: process_module_general(module, data)
	elif module.type == model.ModuleType.PROGRAMMING: process_module_programming(module, data)
	elif module.type == model.ModuleType.QUIZ: process_module_quiz(module, data)
	elif module.type == model.ModuleType.SORTABLE: process_module_sortable(module, data)
	elif module.type == model.ModuleType.TEXT: process_module_text(module, data, os.path.dirname(filename))
	else: module.description = "Neznamy typ modulu"

	# Parsovani tela zadani
	body = replace_h(parse_pandoc('\n'.join(data)))
	module.description = body

# Tady opravdu nema nic byt, general module nema zadnou logiku
def process_module_general(module, lines):
	module.data = '{}'

def process_module_programming(module, lines):
	# Hledame vzorovy kod v zadani
	line = 0
	while (line < len(lines)) and (not re.match(r"^```~python", lines[line])): line += 1
	if line == len(lines): return

	# Hledame konec kodu
	end = line
	while (end < len(lines)) and (not re.match(r"^```", lines[end])): end += 1

	code = '\n'.join(lines[line:end])
	lines = lines[:line]

	# Pridame vzorovy kod do \module.data
	data = json.loads(module.data)
	data['programming']['default_code'] = code
	module.data = json.dumps(data)

def process_module_quiz(module, lines):
	# Hledame jednotlive otazky
	quiz_data = []
	line = 0
	while (line < len(lines)):
		while (line < len(lines)) and (not re.match(r"^##(.*?) (r|c)", lines[line])): line += 1
		text_end = line
		if line == len(lines): break

		# Parsovani otazky
		head = re.match(r"^##(.*?) (r|c)", lines[line])
		question['question'] = parse_pandoc(head.group(1))
		if head.group(2) == 'r':
			question['type'] = 'radio'
		else:
			question['type'] = 'checkbox'

		# Hledame pruvodni text otazky
		line += 1
		end = line
		while (end < len(lines)) and (not re.match(r"^~", lines[end])): end += 1
		question['text'] = parse_pandoc('\n'.join(lines[line:end]))

		# Parsujeme mozne odpovedi
		line = end
		options = []
		correct = []
		while end < len(lines):
			match = re.match(r"^~\s*(.*?)\s*(\*|-)", lines[line]+" -")
			if not match: break;
			options.append(parse_pandoc(match.group(1)).replace("<p>", "").replace("</p>", ""))
			if match.group(2) == '*': correct.append(len(options)-1)

		question['options'] = options
		question['correct'] = correct

		# Pridame otazku
		quiz_data.append(question)

	lines = lines[:text_end]
	module.data = json.dumps(quiz_data)

def process_module_sortable(module, lines):
	pass

def process_module_text(module, lines, path):
	text_data = { "inputs": 0 }

	line = 0
	while (line < len(lines)) and (not re.match(r"^~", lines[line])): line += 1
	text_end = line
	if line == len(lines):
		module.data = json.dumps(text_data)
		return

	inputs_cnt = 0
	diff = []
	while line < len(lines):
		match = re.match(r"^~\s*(.*?)\s*(\*\*(.*?)\*\*|-)", lines[line]+" -")
		if not match: break

		inputs_cnt += 1
		if match.group(3):
			diff.append(match.group(3))
		else:
			if len(diff) > 0: diff.append("")

	text_data['inputs'] = inputs_cnt
	if len(diff) > 0:
		text_data['diff'] = diff
	else:
		# Zkopirujeme eval skript
		target = "data/modules/" + str(module.id) + "/eval.py"
		shutil.copy2(path+"/eval.py", target)
		text_data['eval_script'] = target

	lines = lines[:text_end]
	module.data = json.dumps(text_data)

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

