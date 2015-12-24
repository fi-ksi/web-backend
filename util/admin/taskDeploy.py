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
import util
import pyparsing as pp
from sqlalchemy import and_

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
		# DEBUG:
		#time.sleep(20)
		process_task(task, "data/mooster-task")
	except:
		raise
	finally:
		deployLock.release()

###############################################################################
# Parsovani dat z repozitare:

# Zpracovani cele ulohy
# Data commitujeme do databaze postupne, abychom videli, kde doslo k pripadnemu selhani operace
def process_task(task, path):
	try:
		process_meta(task, path+"/task.json")
		session.commit()

		process_assignment(task, path+"/assignment.md")
		session.commit()

		process_solution(task, path+"/solution.md")
		session.commit()

		process_icons(task, path+"/icons/")
		process_data(task, path+"/data/")

		process_modules(task, path)
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		print "Exiting thread"
		session.close()

def process_meta(task, filename):
	print "Processing meta " + filename

	with open(filename, 'r') as f:
		data = json.loads(f.read())

	task.author = data['author']
	task.time_deadline = data['time_deadline']
	if ('icon_ref' in data) and (data['icon_ref'] is not None):
		task.picture_base = 'data/task-content/' + str(task.id) + '/icon/'
	else:
		task.picture_base = None

	# Parsovani prerekvizit
	if ('prerequisities' in data) and (data['prerequisities'] is not None):
		if task.prerequisite is not None:
			prq = session.query(model.Prerequisite).get(task.prerequisite)
			if prq is None: task.prerequisite = None

		if task.prerequisite is None:
			prq = model.Prerequisite(type=model.PrerequisiteType.ATOMIC, parent=None, task=None)
			try:
				session.add(prq)
			except:
				session.rollback()
				raise

		# Tady mame zaruceno, ze existuje prave jedna korenova prerekvizita
		try:
			parsed = parse_prereq_text(data['prerequisities'])
			parse_prereq_logic(parsed[0], prq)
			session.commit()
		except:
			# TODO: pass meaningful error message to user
			raise

		task.prerequisite = prq.id
	else:
		task.prerequisite = None

# Konvertuje text prerekvizit do seznamu [[['7', '&&', '12'], '||', '4']]
# Seznam na danem zanoreni obsahuje bud teminal, nebo seznam tri prvku
def parse_prereq_text(text):
	number = pp.Regex(r"\d+")
	expr = pp.operatorPrecedence(number, [
			("&&", 2, pp.opAssoc.LEFT, ),
			("||", 2, pp.opAssoc.LEFT, ),
		])
	return expr.parseString(text)

# \logic je vysledek z parsovani parse_prereq_text
# \prereq je aktualne zpracovana prerekvizita (model.Prerequisite)
def parse_prereq_logic(logic, prereq):
	print "Parsing", logic

	if isinstance(logic, (unicode)):
		# ATOMIC
		prereq.type = model.PrerequisiteType.ATOMIC
		prereq.task = int(logic)

		# Smazeme potencialni strom deti
		util.prerequisite.remove_tree(prereq)
		session.commit()

	elif isinstance(logic, (pp.ParseResults)):
		# && or ||
		if logic[1] == '||': prereq.type = model.PrerequisiteType.OR
		else: prereq.type = model.PrerequisiteType.AND
		prereq.task = None

		# Rekurzivne se zanorime
		children = session.query(model.Prerequisite).\
			filter(model.Prerequisite.parent == prereq.id).all()

		# children musi byt prave dve
		while len(children) < 2:
			new_child = model.Prerequisite(type=model.PrerequisiteType.ATOMIC, parent=prereq.id, task=None)
			try:
				session.add(new_child)
				session.commit()
			except:
				session.rollback()
				raise
			children.append(new_child)

		while len(children) > 2:
			util.prerequisite.remove_tree(children[2], True)
			try:
				session.commit()
				children.remove(children[2])
			except:
				session.rollback()
				raise

		# Rekurzivne se zanorime
		parse_prereq_logic(logic[0], children[0])
		parse_prereq_logic(logic[2], children[1])
	else:
		print "Neznamy typ promenne v prerekvizitach"

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
	body = ''.join(parsed)
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
	if not os.path.isdir(target_path): os.makedirs(target_path)
	for f in files:
		if os.path.isfile(source_path+"/"+f):
			shutil.copy2(source_path+"/"+f, target_path+f)

# Zkopiruje veskera data do adresare dat backendu
def process_data(task, source_path):
	target_path = "data/task-content/" + str(task.id) + "/zadani/"
	if not os.path.isdir(target_path): os.makedirs(target_path)
	shutil.rmtree(target_path)
	shutil.copytree(source_path, target_path)

def process_modules(task, git_path):
	# Aktualni moduly v databazi
	modules = session.query(model.Module).\
		filter(model.Module.task == task.id).\
		order_by(model.Module.order).all()

	i = 0
	while (os.path.isdir(git_path+"/module"+str(i+1))):
		if i < len(modules):
			module = modules[i]
			module.order = i
		else:
			module = model.Module(
				task = task.id,
				type = "general",
				name = "",
				order = i
			)
			session.add(module)

		print "Processing module" + str(i+1)
		process_module(module, git_path+"/module"+str(i+1))

		try:
			session.commit()
		except:
			session.rollback()
			raise

		i += 1

	# Smazeme prebytecne moduly
	while i < len(modules):
		module = modules[i]
		try:
			session.delete(module)
			session.commit()
		except:
			session.rollback()

		i += 1

# Zpracovani modulu
# \module je vzdy inicializovany
# \module_path muze byt bez lomitka na konci
def process_module(module, module_path):
	process_module_json(module, module_path+"/module.json")
	process_module_md(module, module_path+"/module.md")

# Zpracovani souboru module.json
def process_module_json(module, filename):
	print "Processing module json"
	with open(filename, 'r') as f:
		data = json.loads(f.read())

	if data['type'] == 'text': module.type = model.ModuleType.TEXT
	elif data['type'] == 'general': module.type = model.ModuleType.GENERAL
	elif data['type'] == 'programming': module.type = model.ModuleType.PROGRAMMING
	elif data['type'] == 'quiz': module.type = model.ModuleType.QUIZ
	elif data['type'] == 'sortable': module.type = model.ModuleType.SORTABLE
	else: module.type = model.ModuleType.GENERAL

	module.max_points = data['max_points']
	module.autocorrect = data['autocorrect']
	module.bonus = data['bonus'] if 'bonus' in data else False
	module.action = data['action'] if 'action' in data else ""

# Zpracovani module.md
# Pandoc spoustime az uplne nakonec, abychom mohli provest analyzu souboru.
def process_module_md(module, filename):
	print "Processing module md"

	with open(filename, 'r') as f:
		data = f.readlines()

	# Hledame nazev modulu na nultem radku
	name = re.search(r"(# .*)", data[0])
	if name is not None:
		module.name = re.search(r"<h1(.*?)>(.*?)</h1>", parse_pandoc(name.group(1))).group(2)
		data.pop(0)
	else:
		module.name = "Nazev modulu nenalezen"

	print "Processing specific module"

	# Ukolem nasledujicich metod je zpracovat logiku modulu a v \data zanechat uvodni text
	if module.type == model.ModuleType.GENERAL: data = process_module_general(module, data)
	elif module.type == model.ModuleType.PROGRAMMING: data = process_module_programming(module, data, os.path.dirname(filename))
	elif module.type == model.ModuleType.QUIZ: data = process_module_quiz(module, data)
	elif module.type == model.ModuleType.SORTABLE: data = process_module_sortable(module, data)
	elif module.type == model.ModuleType.TEXT: data = process_module_text(module, data, os.path.dirname(filename))
	else: module.description = "Neznamy typ modulu"

	print "Processing body"

	# Parsovani tela zadani
	body = replace_h(parse_pandoc(''.join(data)))
	module.description = body

# Tady opravdu nema nic byt, general module nema zadnou logiku
def process_module_general(module, lines):
	module.data = '{}'
	return lines

def process_module_programming(module, lines, source_path):
	# Hledame vzorovy kod v zadani
	line = 0
	while (line < len(lines)) and (not re.match(r"^```~python", lines[line])): line += 1
	if line == len(lines): return

	# Hledame konec kodu
	end = line+1
	while (end < len(lines)) and (not re.match(r"^```", lines[end])): end += 1

	code = ''.join(lines[line+1:end])

	# Pridame vzorovy kod do \module.data
	data = {}
	old_data = json.loads(module.data)
	data['programming'] = old_data['programming'] if 'programming' in old_data else {}
	data['programming']['default_code'] = code

	# Zkopirujeme skripty do prislusnych adresaru
	target_path = "data/modules/" + str(module.id) + "/"
	files = [ "eval.py", "merge.py", "post.py", "stdin.txt" ]
	if not os.path.isdir(target_path): os.makedirs(target_path)
	for f in files:
		if os.path.isfile(source_path+"/"+f):
			shutil.copy2(source_path+"/"+f, target_path+f)

	data['programming']['merge_script'] = target_path + "merge.py"
	data['programming']['stdin'] = target_path + "stdin.txt"
	data['programming']['post_trigger_script'] = target_path + "post.py"
	data['programming']['check_script'] = target_path + "eval.py"

	module.data = json.dumps(data, indent=2)
	return lines[:line]

def process_module_quiz(module, lines):
	# Hledame jednotlive otazky
	quiz_data = []
	line = 0
	text_end = 0
	while (line < len(lines)):
		while (line < len(lines)) and (not re.match(r"^##(.*?) \((r|c)\)", lines[line])): line += 1
		if text_end == 0: text_end = line
		if line == len(lines): break

		# Parsovani otazky
		question = {}
		head = re.match(r"^##(.*?) \((r|c)\)", lines[line])
		question['question'] = re.match("<p>(.*)</p>", parse_pandoc(head.group(1))).group(1)
		if head.group(2) == 'r':
			question['type'] = 'radio'
		else:
			question['type'] = 'checkbox'

		# Hledame pruvodni text otazky
		line += 1
		end = line
		while (end < len(lines)) and (not re.match(r"^~", lines[end])): end += 1
		question['text'] = parse_pandoc(''.join(lines[line:end]))

		# Parsujeme mozne odpovedi
		line = end
		options = []
		correct = []
		while line < len(lines):
			match = re.match(r"^~\s*(.*?)\s*(\*|-)", lines[line]+" -")
			if not match: break;
			options.append(parse_pandoc(match.group(1)).replace("<p>", "").replace("</p>", "").replace('\n', ''))
			if match.group(2) == '*': correct.append(len(options)-1)

			line += 1

		question['options'] = options
		question['correct'] = correct

		# Pridame otazku
		quiz_data.append(question)

	module.data = json.dumps({ 'quiz': quiz_data }, indent=2)
	return lines[:text_end]

def process_module_sortable(module, lines):
	sort_data = {}
	sort_data['fixed'] = []
	sort_data['movable'] = []
	sort_data['correct'] = []
	module.data = json.dumps({ 'sortable': sort_data }, indent=2)
	return lines

def process_module_text(module, lines, path):
	text_data = { "inputs": 0 }

	line = 0
	while (line < len(lines)) and (not re.match(r"^~", lines[line])): line += 1
	text_end = line
	if line >= len(lines):
		module.data = json.dumps(text_data, indent=2)
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

		line += 1

	text_data['inputs'] = inputs_cnt
	if len(diff) > 0:
		text_data['diff'] = diff
	else:
		# Zkopirujeme eval skript
		target = "data/modules/" + str(module.id) + "/eval.py"
		shutil.copy2(path+"/eval.py", target)
		text_data['eval_script'] = target

	module.data = json.dumps({ 'text': text_data }, indent=2)
	return lines[:text_end]

###############################################################################
# Pomocne parsovaci funkce:

# Parsovani stringu \source pandocem
def parse_pandoc(source):
	return pypandoc.convert(source, 'html5', format='md', extra_args=['--smart', '--mathjax'])

# <h2> -> <h3>, <h3> -> <h4>, <h4> -> <h5> (to musi stacit)
def replace_h(source):
	return source.replace("<h4", "<h5").replace("</h4>", "</h5>"). \
		replace("<h3", "<h4").replace("</h3>", "</h4>"). \
		replace("<h2", "<h3").replace("</h2>", "</h3>")

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
	return re.sub(r"data/", util.config.ksi_web()+":3000/taskContent/"+str(task.id)+"/zadani/", source)

###############################################################################

