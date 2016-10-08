# -*- coding: utf-8 -*-

#from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

#from db import engine
from lockfile import LockFile
import model, json, time, pypandoc, re, os, shutil, util, git, sys, traceback, datetime
import pyparsing as pp
import dateutil.parser
from humanfriendly import parse_size

# Deploy muze byt jen jediny na cely server -> pouzivame lockfile.
LOCKFILE = '/var/lock/ksi-task-deploy'
LOGFILE = 'data/deploy.log'

# Deploy je spousten v samostatnem vlakne.
session = None
eval_public = True

"""
Tato funkce je spoustena v samostatnem vlakne.
Je potreba vyuzit podpory vice vlaken v SQL alchemy:
 * V ZADNEM PRIPADE se neodkazovat na db.py a zejmena na session !
 * scoped vzniklo z scoped_session(...), vyuzit tuto scoped session
 * ze scoped_session si vytvorime session, kterou dale pouzivame
 * na konci projistotu scoped.remove(), ale podle dokumentace neni potreba
Vyse zmimeny postup by mel byt v souladu s dokumentaci k sqlalchemy.
 * !!! funkci nelze predavat model.Task, protoze tento objekt je vazany na session;
   my si ale vytvarime vlasnti session ...
Doporucuje se, ale uloha, se kterou je tato funkce volana uz mela nastaveno
task.deploy_status = 'deploying', nebot nastaveni v tomto vlakne se muze
projevit az za nejakou dobu, behem ktere by GET mohl vratit "done", coz nechceme.
"""
def deploy(task_id, deployLock, scoped):
	try:
		# Init session
		global session
		session = scoped()
		task = session.query(model.Task).get(task_id)

		global eval_public
		eval_public = True

		# Create log file
		create_log(task, "deploying")
		task.deploy_status = 'deploying'
		task.deploy_date = datetime.datetime.utcnow()
		session.commit()

		# Init repo object
		repo = git.Repo(util.git.GIT_SEMINAR_PATH)
		assert not repo.bare

		# Fetch origin
		#if not task.git_branch in repo.branches:
		log("Fetching origin...")
		for fetch_info in repo.remotes.origin.fetch():
			if str(fetch_info.ref) == "origin/"+task.git_branch:
				log("Updated " + str(fetch_info.ref) + " to " + str(fetch_info.commit))

		# Check out task branch
		log("Checking out " + task.git_branch)
		log(repo.git.checkout(task.git_branch))

		# Discard all local changes
		log("Hard-reseting to origin/" + task.git_branch)
		repo.git.reset("--hard", "origin/"+task.git_branch)

		# Check if task path exists
		if not os.path.isdir(util.git.GIT_SEMINAR_PATH + task.git_path):
			log("Repo dir does not exist")
			task.deploy_status = 'error'
			session.commit()
			return

		# Parse task
		log("Parsing " + util.git.GIT_SEMINAR_PATH+task.git_path)
		process_task(task, util.git.GIT_SEMINAR_PATH+task.git_path)

		# Update git entries in db
		task.evaluation_public |= eval_public
		task.git_commit = repo.head.commit.hexsha
		task.deploy_status = 'done'

		# Update thread name
		thread = session.query(model.Thread).get(task.thread)
		if thread: thread.title = task.title

		session.commit()
	except Exception as e:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		log("Exception: " + traceback.format_exc())
		session.rollback()
		try:
			task.deploy_status = 'error'
			session.commit()
		except:
			session.rollback()
	finally:
		deployLock.release()
		log("Done")
		session.close()
		scoped.remove()

###############################################################################
# Parsovani dat z repozitare:

# Zpracovani cele ulohy
# Data commitujeme do databaze postupne, abychom videli, kde doslo k pripadnemu selhani operace
def process_task(task, path):
	try:
		process_meta(task, path+"/task.json")
		session.commit()

		log("Processing assignment")
		process_assignment(task, path+"/assignment.md")
		session.commit()

		log("Processing solution")
		process_solution(task, path+"/solution.md")
		session.commit()

		log("Processing icons")
		process_icons(task, path+"/icons/")
		process_data(task, path+"/data/")

		log("Processing modules")
		process_modules(task, path)
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		log("Task processing done")

def process_meta(task, filename):
	def local2UTC(LocalTime):
		EpochSecond = time.mktime(LocalTime.timetuple())
		return datetime.datetime.utcfromtimestamp(EpochSecond)

	log("Processing meta " + filename)

	with open(filename, 'r') as f:
		data = json.loads(f.read().decode('utf-8-sig'))

	task.author = data['author']

	if 'date_deadline' in data:
		task.time_deadline = local2UTC(dateutil.parser.parse(data['date_deadline']).replace(hour=23, minute=59, second=59))
	else:
		task.time_deadline = data['time_deadline']

	if ('icon_ref' in data) and (data['icon_ref'] is not None):
		# Osetreni reference pres 2 ulohy
		tmp_task = session.query(model.Task).get(data['icon_ref'])
		if tmp_task.picture_base:
			task.picture_base = tmp_task.picture_base
		else:
			task.picture_base = '/taskContent/' + str(data['icon_ref']) + '/icon/'
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
				session.commit()
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
	if logic:
		log("Parsing " + str(logic))

	if isinstance(logic, (unicode)):
		# ATOMIC
		prereq.type = model.PrerequisiteType.ATOMIC
		prereq.task = int(logic)

		# Smazeme potencialni strom deti
		for child in prereq.children:
			session.delete(child)
		session.commit()

	elif isinstance(logic, (pp.ParseResults)):
		# && or ||
		if logic[1] == '||': prereq.type = model.PrerequisiteType.OR
		else: prereq.type = model.PrerequisiteType.AND
		prereq.task = None

		# Rekurzivne se zanorime
		children = session.query(model.Prerequisite).\
			filter(and_(model.Prerequisite.parent != None, model.Prerequisite.parent == prereq.id)).all()

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

		try:
			while len(children) > 2:
				session.delete(children[2])
				session.commit()
				children.remove(children[2])
		except:
			session.rollback()
			raise

		# Rekurzivne se zanorime
		parse_prereq_logic(logic[0], children[0])
		parse_prereq_logic(logic[2], children[1])
	else:
		log("Neznamy typ promenne v prerekvizitach")

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
		task.solution = parse_simple_text(task, data)
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
	if os.path.isdir(source_path):
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

		log("Processing module" + str(i+1))
		process_module(module, git_path+"/module"+str(i+1), task)

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
			raise

		i += 1

# Zpracovani modulu
# \module je vzdy inicializovany
# \module_path muze byt bez lomitka na konci
def process_module(module, module_path, task):
	specific = process_module_json(module, module_path+"/module.json")
	process_module_md(module, module_path+"/module.md", specific, task)

# Zpracovani souboru module.json
def process_module_json(module, filename):
	log("Processing module json")
	with open(filename, 'r') as f:
		data = json.loads(f.read().decode('utf-8-sig'))

	if data['type'] == 'text': module.type = model.ModuleType.TEXT
	elif data['type'] == 'general': module.type = model.ModuleType.GENERAL
	elif data['type'] == 'programming': module.type = model.ModuleType.PROGRAMMING
	elif data['type'] == 'quiz': module.type = model.ModuleType.QUIZ
	elif data['type'] == 'sortable': module.type = model.ModuleType.SORTABLE
	else: module.type = model.ModuleType.GENERAL

	# JSON parametry pro specificky typ modulu
	specific = data[data['type']] if data['type'] in data else {}

	module.max_points = data['max_points']
	module.autocorrect = data['autocorrect']
	module.bonus = data['bonus'] if 'bonus' in data else False
	module.action = data['action'] if 'action' in data else ""

	global eval_public
	if not module.autocorrect: eval_public = False

	return specific

# Zpracovani module.md
# Pandoc spoustime az uplne nakonec, abychom mohli provest analyzu souboru.
def process_module_md(module, filename, specific, task):
	log("Processing module md")

	with open(filename, 'r') as f:
		data = f.readlines()

	# Hledame nazev modulu na nultem radku
	name = re.search(r"(# .*)", data[0])
	if name is not None:
		module.name = re.search(r"<h1(.*?)>(.*?)</h1>", parse_pandoc(name.group(1))).group(2)
		data.pop(0)
	else:
		module.name = "Nazev modulu nenalezen"

	# Ukolem nasledujicich metod je zpracovat logiku modulu a v \data zanechat uvodni text
	if module.type == model.ModuleType.GENERAL: data = process_module_general(module, data, specific)
	elif module.type == model.ModuleType.PROGRAMMING: data = process_module_programming(module, data, specific, os.path.dirname(filename))
	elif module.type == model.ModuleType.QUIZ: data = process_module_quiz(module, data, specific, task)
	elif module.type == model.ModuleType.SORTABLE: data = process_module_sortable(module, data, specific)
	elif module.type == model.ModuleType.TEXT: data = process_module_text(module, data, specific, os.path.dirname(filename))
	else: module.description = "Neznamy typ modulu"

	log("Processing body")

	# Parsovani tela zadani
	module.description = parse_simple_text(task, ''.join(data))

# Tady opravdu nema nic byt, general module nema zadnou logiku
def process_module_general(module, lines, specific):
	log("Processing general module")
	module.data = '{}'
	return lines

def process_module_programming(module, lines, specific, source_path):
	log("Processing programming module")

	# Hledame vzorovy kod v zadani
	line = 0
	while (line < len(lines)) and (not re.match(r"^```~python", lines[line])): line += 1
	if line == len(lines): return lines

	# Hledame konec kodu
	end = line+1
	while (end < len(lines)) and (not re.match(r"^```", lines[end])): end += 1

	code = ''.join(lines[line+1:end])

	# Pridame vzorovy kod do \module.data
	data = {}
	#old_data = json.loads(module.data) if module.data else None
	#data['programming'] = old_data['programming'] if (old_data) and ('programming' in old_data) else {}
	data['programming'] = {}
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
	if not os.path.isfile(source_path+"/stdin.txt"):
		open(target_path + "stdin.txt", "a").close() # create empty stdin
	if os.path.isfile(source_path+"/post.py"): data['programming']['post_trigger_script'] = target_path + "post.py"
	data['programming']['check_script'] = target_path + "eval.py"

	# direktivy z module.json
	if 'timeout' in specific: data['programming']['timeout'] = specific['timeout']
	if 'args' in specific: data['programming']['args'] = specific['args']
	if 'heaplimit' in specific:
		data['programming']['heaplimit'] = parse_size(specific['heaplimit'])
		log("Heaplimit parsed as " + str(data['programming']['heaplimit']) + " bytes")

	module.data = json.dumps(data, indent=2)
	return lines[:line]

def process_module_quiz(module, lines, specific, task):
	log("Processing quiz module")

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
		question['text'] = parse_simple_text(task, ''.join(lines[line:end]))

		# Parsujeme mozne odpovedi
		line = end
		options = []
		correct = []
		while line < len(lines):
			match = re.match(r"^~\s*(.*?)\s*(\*|-)(\s|-)*$", lines[line]+" -")
			if not match: break
			options.append(parse_pandoc(match.group(1)).replace("<p>", "").replace("</p>", "").replace('\n', ''))
			if match.group(2) == '*': correct.append(len(options)-1)

			line += 1

		question['options'] = options
		question['correct'] = correct

		# Pridame otazku
		quiz_data.append(question)

	module.data = json.dumps({ 'quiz': quiz_data }, indent=2)
	return lines[:text_end]

def process_module_sortable(module, lines, specific):
	log("Processing sortable module")

	sort_data = {}
	sort_data['fixed'] = []
	sort_data['movable'] = []
	sort_data['correct'] = []

	line = 0
	while (line < len(lines)) and (not re.match(r"^~", lines[line])): line += 1
	text_end = line

	# Parsovani fixed casti
	while line < len(lines):
		match = re.match(r"^~\s*(.*)", lines[line])
		if not match: break
		parsed = parse_pandoc(match.group(1)).replace("<p>", "").replace("</p>", "").replace('\n', '')
		sort_data['fixed'].append( { 'content': parsed, 'offset': get_sortable_offset(parsed) } )
		line += 1

	# Volny radek mezi fixed a movable casti
	line += 1

	# Movable cast
	while line < len(lines):
		match = re.match(r"^~\s*(.*)", lines[line])
		if not match: break
		parsed = parse_pandoc(match.group(1)).replace("<p>", "").replace("</p>", "").replace('\n', '')
		sort_data['movable'].append( { 'content': parsed, 'offset': get_sortable_offset(parsed) } )
		line += 1

	# Parsovani spravnych poradi
	while line < len(lines):
		match = re.match(r"^\s*\((((a|b)\d+,)*(a|b)\d+)\)", lines[line])
		if match:
			sort_data['correct'].append(match.group(1).split(','))
		line += 1

	module.data = json.dumps({ 'sortable': sort_data }, indent=2)
	return lines[:text_end]

def get_sortable_offset(text):
	if re.match(r"^(if|Vstup:|while|for|def) ", text): return 1
	elif re.match(r"^(fi|od)$", text) or re.match(r"^return ", text): return -1
	return 0

def process_module_text(module, lines, specific, path):
	log("Processing text module")

	text_data = { "inputs": 0 }

	line = 0
	while (line < len(lines)) and (not re.match(r"^~", lines[line])): line += 1
	text_end = line
	if line >= len(lines):
		module.data = json.dumps(text_data, indent=2)
		return lines

	inputs_cnt = 0
	diff = []
	questions = []
	while line < len(lines):
		match = re.match(r"^~\s*(.*?)\s*(\*\*(.*?)\*\*|-)", lines[line]+" -")
		if not match: break

		questions.append(match.group(1))

		inputs_cnt += 1
		if match.group(3):
			diff.append(match.group(3))
		else:
			if len(diff) > 0: diff.append("")

		line += 1

	text_data['questions'] = questions
	text_data['inputs'] = inputs_cnt
	if len(diff) > 0:
		text_data['diff'] = diff
	else:
		# Zkopirujeme eval skript
		target_path = "data/modules/" + str(module.id) + "/"
		if not os.path.isdir(target_path): os.makedirs(target_path)
		shutil.copy2(path+"/eval.py", target_path+"eval.py")
		text_data['eval_script'] = target_path+"eval.py"

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
		replace("<h2", "<h3").replace("</h2>", "</h3>"). \
		replace("<h1", "<h3").replace("</h1>", "</h3>")

# Stara se o vnitrek jednoho pseudokodu
# na vstup dostane \match, \match.group() obsahuje "<ksi-pseudocode>TEXT</ksi-pseudocode>"
def one_ksi_pseudocode(match):
	source = match.group()
	source = re.sub(ur"(function|funkce|procedure|Vstup|Výstup|then|return|else)", r"**\1**", source)
	source = re.sub(ur"(if|while|for) ", r"**\1** ", source) # Za klicovymslovem musi nasledovat mezera
	source = re.sub(ur" (do)", r" **\1**", source) # Pred klicovymslovem musi nasledovat mezera
	source = re.sub(ur"\n(\s*)(od|fi)\s*(\\?)\n", r"\n\1**\2**\3\n", source) # Klicove slovo musi byt na samostatnem radku
	source = re.sub(r"<ksi-pseudocode>", r"<div style='padding-left:20px'>\n", source)
	source = re.sub(r"</ksi-pseudocode>", r"</div>", source)
	source = re.sub(r"\n", r"\n\n", source) # Takto donutime pandoc davat kazdy radek do samostateho odstavce
	source = re.sub(r"(\t|    )", r"&emsp;", source)
	return source

# Nahrazuje <ksi-pseudocode> za prislusne HTML
def ksi_pseudocode(source):
	source = re.sub(u"<ksi-pseudocode>\n((.|\n)*?)</ksi-pseudocode>", one_ksi_pseudocode, source)
	return source

# Nahrauje jedno <ksi-collapse>
def one_ksi_collapse(match):
	global coll_id
	coll_id += 1

	return """
<div class="panel panel-ksi panel-group">
<div class="panel-heading panel-heading-ksi"><h4 class="panel-title"><a data-toggle="collapse" href="#collapse""" + str(coll_id) + """">""" + match.group(1) + """</a></h4></div>
<div id="collapse""" + str(coll_id) + """" class="panel-collapse collapse">
<div class="panel-body">"""

# Nahrazuje <ksi-collapse> za HTML plne silenych <div>u
def ksi_collapse(source):
	global coll_id
	coll_id = 0
	source = re.sub(r"<ksi-collapse title=\"(.*?)\">", one_ksi_collapse, source)
	return source.replace("</ksi-collapse>", "</div></div></div>")

# Nahrazuje odkazy do data/ za odkazy do backendu
def change_links(task, source):
	return re.sub(r"data/", util.config.ksi_web()+":3000/taskContent/"+str(task.id)+"/zadani/", source)

def parse_simple_text(task, text):
	return change_links(task, replace_h(parse_pandoc(ksi_collapse(ksi_pseudocode(text)))))

###############################################################################

def create_log(task, status):
	with open(LOGFILE, 'w') as f:
		f.write(str(task.id) + '\n')

def log(text):
	with open(LOGFILE, 'a') as f:
		f.write(text+'\n')

###############################################################################
