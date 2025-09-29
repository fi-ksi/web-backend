from dataclasses import dataclass
import datetime
import json
import os
import random
import re
import shutil
import string
import sys
import time
import traceback
from typing import Callable, List, Optional
from typing import Dict, Union

import dateutil.parser
import git
import pypandoc
import pyparsing as pp
from lockfile import LockFile
from sqlalchemy import and_
from sqlalchemy.orm import Session

import model
import util
from util.logger import get_log
from util.task import max_points

# Deploy muze byt jen jediny na cely server -> pouzivame lockfile.
LOCKFILE = '/var/lock/ksi-task-deploy'
LOGFILE = 'data/deploy.log'

# Deploy je spousten v samostatnem vlakne.
session: Optional[Session] = None
eval_public = True


@dataclass
class ReplacementMetadata:
    """
    Class for holding metadata about current replacements of markdown code
    Useful for keeping track of global ids across assigment and multiple modules
    """
    collapse_max_id: int

    @staticmethod
    def get_default() -> "ReplacementMetadata":
        return ReplacementMetadata(collapse_max_id=0)


def deploy(task_id: int, year_id: int, deployLock: LockFile, scoped: Callable) -> None:
    """
    Tato funkce je spoustena v samostatnem vlakne.
    Je potreba vyuzit podpory vice vlaken v SQL alchemy:
     * V ZADNEM PRIPADE se neodkazovat na db.py a zejmena na session !
     * scoped vzniklo z scoped_session(...), vyuzit tuto scoped session
     * ze scoped_session si vytvorime session, kterou dale pouzivame
     * na konci projistotu scoped.remove(), ale podle dokumentace neni potreba
    Vyse zmimeny postup by mel byt v souladu s dokumentaci k sqlalchemy.
     * !!! funkci nelze predavat model.Task, protoze tento objekt je vazany na
       session; my si ale vytvarime vlasnti session ...
    Doporucuje se, ale uloha, se kterou je tato funkce volana uz mela nastaveno
    task.deploy_status = 'deploying', nebot nastaveni v tomto vlakne se muze
    projevit az za nejakou dobu, behem ktere by GET mohl vratit "done", coz
    nechceme.
    """

    try:
        # Init session
        global session
        session = scoped()
        task = session.query(model.Task).get(task_id)
        year = session.query(model.Year).get(year_id)

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
        # if not task.git_branch in repo.branches:
        log("Fetching origin...")
        for fetch_info in repo.remotes.origin.fetch():
            if str(fetch_info.ref) == "origin/" + task.git_branch:
                log("Updated " + str(fetch_info.ref) + " to " +
                    str(fetch_info.commit))

        # Check out task branch
        log("Checking out " + task.git_branch)
        log(repo.git.checkout(task.git_branch))

        # Discard all local changes
        log("Hard-reseting to origin/" + task.git_branch)
        repo.git.reset("--hard", "origin/" + task.git_branch)

        # Check if task path exists
        if not os.path.isdir(util.git.GIT_SEMINAR_PATH + task.git_path):
            log("Repo dir does not exist")
            task.deploy_status = 'error'
            session.commit()
            return

        # Save max points before for modifying the point pad
        max_points_before: float = max_points(task.id)
        log(f"Current task max points: {max_points_before}", task=task_id)
        log(f"Current year point pad: {year.point_pad}", task=task_id)

        # Parse task
        log("Parsing " + util.git.GIT_SEMINAR_PATH + task.git_path)
        process_task(task, util.git.GIT_SEMINAR_PATH + task.git_path)

        # Compare the max points and edit the point pad accordingly
        max_points_now: float = max_points(task.id)
        max_points_diff = max_points_before - max_points_now
        log(f"New task max points: {max_points_now} (before {max_points_before}, diff {max_points_diff})", task=task_id)

        if max_points_diff == 0.0:
            log("Point diff is zero, no change is necessary", task=task_id)
        elif year.point_pad == 0.0:
            log("The year's point pad is already zero, not modifying it", task=task_id)
        else:
            new_point_pad = max(0.0, year.point_pad + max_points_diff)
            log(f"Setting the year's point pad to {new_point_pad}", task=task_id)
            # year.point_pad = new_point_pad  # TODO disabled as it conflicts that the point pad is the maximum of the points

        # Update git entries in db
        if task.time_deadline > datetime.datetime.utcnow():
            # Tak is being deployed before deadline
            task.evaluation_public = eval_public
        else:
            # Task is deployed after deadline
            # |= is important for deploying after task is published
            task.evaluation_public |= eval_public

        task.git_commit = repo.head.commit.hexsha
        task.deploy_status = 'done'

        # Update thread name
        thread = session.query(model.Thread).get(task.thread)
        if thread:
            thread.title = task.title

        session.commit()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception: " + traceback.format_exc(), task=task_id)
        session.rollback()
        try:
            task.deploy_status = 'error'
            session.commit()
        except BaseException:
            session.rollback()
    finally:
        if deployLock.is_locked():
            deployLock.release()
        log("Done")
        session.close()
        scoped.remove()

###############################################################################
# Parsovani dat z repozitare:


def process_task(task: model.Task, path: str) -> None:
    """Zpracovani cele ulohy
    Data commitujeme do databaze postupne, abychom videli, kde doslo k
    pripadnemu selhani operace.
    """

    try:
        DATAPATH = f"data/task-content/{task.id}"

        process_meta(task, path + "/task.json")
        session.commit()

        replacement_metadata = ReplacementMetadata.get_default()

        # Remove non-mangled path
        to_remove = f"{DATAPATH}/zadani"
        if os.path.isdir(to_remove):
            log(f"Removing old {to_remove}...")
            shutil.rmtree(to_remove)

        task.mangled_datadir = mangled_dirname(
            f"data/task-content/{task.id}", "zadani_")
        task.mangled_soldir = mangled_dirname(
            f"data/task-content/{task.id}", "reseni_")

        log("Processing assignment")
        process_assignment(task, path + "/assignment.md", replacement_metadata)
        session.commit()

        log("Processing solution")
        process_solution(task, path + "/solution.md", replacement_metadata)
        session.commit()

        log("Processing icons & data")
        copy_icons(task, path + "/icons/")
        copy_data(task, f"{path}/data",
                  os.path.join(DATAPATH, task.mangled_datadir))
        copy_data(task, f"{path}/data_solution",
                  os.path.join(DATAPATH, task.mangled_soldir))

        log("Processing modules")
        process_modules(task, path, replacement_metadata)
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        log("Task processing done")


def process_meta(task: model.Task, filename: str) -> None:
    def local2UTC(LocalTime: datetime) -> datetime:
        EpochSecond = time.mktime(LocalTime.timetuple())
        return datetime.datetime.utcfromtimestamp(EpochSecond)

    log("Processing meta " + filename)

    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.loads(f.read())

    task.author = data['author']
    if 'co_author' in data:
        task.co_author = data['co_author']
    else:
        task.co_author = None

    if 'date_deadline' in data:
        task.time_deadline = local2UTC(
            dateutil.parser.parse(data['date_deadline']).
            replace(hour=23, minute=59, second=59))
    else:
        task.time_deadline = data['time_deadline']

    if ('icon_ref' in data) and (data['icon_ref'] is not None):
        # Osetreni reference pres 2 ulohy
        tmp_task = session.query(model.Task).get(data['icon_ref'])
        if tmp_task.picture_base:
            task.picture_base = tmp_task.picture_base
        else:
            task.picture_base = '/taskContent/' + \
                str(data['icon_ref']) + '/icon/'
    else:
        task.picture_base = None

    # Parsovani prerekvizit
    if ('prerequisities' in data) and (data['prerequisities'] is not None):
        if type(data['prerequisities']) is int:
            # Sometimes, organizes assign ID as a number instead of a string
            data['prerequisities'] = str(data['prerequisities'])

        if task.prerequisite is not None:
            prq = session.query(model.Prerequisite).get(task.prerequisite)
            if prq is None:
                task.prerequisite = None
        else:
            prq = model.Prerequisite(
                type=model.PrerequisiteType.ATOMIC,
                parent=None,
                task=None
            )

            try:
                session.add(prq)
                session.commit()
            except BaseException:
                session.rollback()
                raise

        # Tady mame zaruceno, ze existuje prave jedna korenova prerekvizita
        try:
            parsed = parse_prereq_text(data['prerequisities'])
            parse_prereq_logic(parsed[0], prq, task.wave_.year)
            
            # Kontrola cyklických prerekvizit
            cycle_check = check_prerequisite_cycles(task.id, prq, task.wave_.year)
            if cycle_check:
                log(f"WARNING: Cyklická prerekvizita detekována pro úlohu {task.id}: {cycle_check}")
                raise Exception(f"Cyklická prerekvizita detekována: {cycle_check}")
            
            session.commit()
        except BaseException:
            # TODO: pass meaningful error message to user
            raise

        task.prerequisite = prq.id
    else:
        task.prerequisite = None


def parse_prereq_text(text: str):
    """Konvertuje text prerekvizit do seznamu [[['7', '&&', '12'], '||', '4']]
    Seznam na danem zanoreni obsahuje bud teminal, nebo seznam tri prvku
    """

    # can be task id or its directory name
    task_reference = pp.Regex(r"(\d+)|(uloha_\d+_\w+)")
    expr = pp.operatorPrecedence(task_reference, [
        ("&&", 2, pp.opAssoc.LEFT, ),
        ("||", 2, pp.opAssoc.LEFT, ),
    ])
    return expr.parseString(text)


def _collect_task_dependencies_from_prereq(prereq: model.Prerequisite, task_id: int, visited_tasks: set) -> Optional[str]:
    """
    Rekurzivně sbírá všechny task_id ze stromu prerekvizit a kontroluje cykly
    
    :param prereq: prerekvizita k prohledání
    :param task_id: ID úlohy, pro kterou kontrolujeme prerekvizity
    :param visited_tasks: množina již navštívených úloh
    :return: None pokud není cykl, jinak popis cyklu
    """
    if session is None:
        return None
        
    if prereq.type == model.PrerequisiteType.ATOMIC and prereq.task:
        if prereq.task == task_id:
            return f"úloha {task_id} závisí sama na sobě"
        if prereq.task in visited_tasks:
            return f"cyklická závislost zahrnující úlohu {prereq.task}"
        
        visited_tasks.add(prereq.task)
        
        task_obj = session.query(model.Task).get(prereq.task)
        if task_obj and task_obj.prerequisite_obj:
            cycle = _collect_task_dependencies_from_prereq(task_obj.prerequisite_obj, task_id, visited_tasks.copy())
            if cycle:
                return cycle
                
    elif prereq.type in [model.PrerequisiteType.AND, model.PrerequisiteType.OR]:
        for child in prereq.children:
            cycle = _collect_task_dependencies_from_prereq(child, task_id, visited_tasks.copy())
            if cycle:
                return cycle
    
    return None


def check_prerequisite_cycles(task_id: int, prereq_root: model.Prerequisite, year: int) -> Optional[str]:
    """
    Kontroluje, zda nejsou prerekvizity cyklické
    
    :param task_id: ID úlohy, pro kterou kontrolujeme prerekvizity
    :param prereq_root: kořenová prerekvizita
    :param year: rok, ve kterém se kontrolují úlohy
    :return: None pokud není cykl, jinak popis cyklu
    """
    return _collect_task_dependencies_from_prereq(prereq_root, task_id, set())


def parse_prereq_logic(logic, prereq, year: int) -> None:
    """'logic' je vysledek z parsovani parse_prereq_text
    'prereq' je aktualne zpracovana prerekvizita (model.Prerequisite)
    """

    if logic:
        log("Parsing " + str(logic))

    if isinstance(logic, (str)):
        # ATOMIC
        prereq.type = model.PrerequisiteType.ATOMIC

        try:
            prereq_id = int(logic)
        except ValueError:
            log("Finding the task by its git path")
            waves = session.query(model.Wave).\
                filter(model.Wave.year == year).\
                all()
            wave_ids = [wave.id for wave in waves]

            prereq_task = session.query(model.Task).\
                filter(and_(model.Task.wave.in_(wave_ids), model.Task.git_path.like(f'%/{logic}'))).\
                first()
            prereq_id = prereq_task.id
        prereq.task = prereq_id

        # Smazeme potencialni strom deti
        for child in prereq.children:
            session.delete(child)
        session.commit()

    elif isinstance(logic, (pp.ParseResults)):
        if len(logic) > 3:
            log('WARNING: Wrong format of `prerequisite` string, you can enter'
                ' at most one operator at each level, ignoring some '
                'prerequisities!')

        # && or ||
        if logic[1] == '||':
            prereq.type = model.PrerequisiteType.OR
        else:
            prereq.type = model.PrerequisiteType.AND
        prereq.task = None

        # Rekurzivne se zanorime
        children = session.query(model.Prerequisite).\
            filter(and_(model.Prerequisite.parent is not None,
                        model.Prerequisite.parent == prereq.id)).\
            all()

        # children musi byt prave dve
        while len(children) < 2:
            new_child = model.Prerequisite(
                type=model.PrerequisiteType.ATOMIC,
                parent=prereq.id,
                task=None
            )

            try:
                session.add(new_child)
                session.commit()
            except BaseException:
                session.rollback()
                raise
            children.append(new_child)

        try:
            while len(children) > 2:
                session.delete(children[2])
                session.commit()
                children.remove(children[2])
        except BaseException:
            session.rollback()
            raise

        # Rekurzivne se zanorime
        parse_prereq_logic(logic[0], children[0], year)
        parse_prereq_logic(logic[2], children[1], year)
    else:
        log('ERROR: Unknown type of variable in prerequisite!')


def process_assignment(task, filename: str, replacement_metadata: Optional[ReplacementMetadata] = None) -> None:
    """Vlozi zadani ulohy do databaze"""

    with open(filename, 'r') as f:
        data = f.read()
    data = format_custom_tags(data)
    data = ksi_pseudocode(data)
    data = ksi_collapse(data, replacement_metadata)
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
    body = add_table_class(body)
    task.body = body


def process_solution(task, filename, replacement_metadata: Optional[ReplacementMetadata] = None):
    """Add solution to database."""
    if os.path.isfile(filename):
        with open(filename, 'r') as f:
            data = f.read()
        task.solution = parse_simple_text(task, data, replacement_metadata)
    else:
        task.solution = None


def copy_icons(task: model.Task, source_path: str) -> None:
    """Copy icons from repository to backend path."""
    target_path = f"data/task-content/{task.id}/icon/"
    files = ["base.svg", "correcting.svg", "locked.svg", "done.svg"]
    if not os.path.isdir(target_path):
        os.makedirs(target_path)
    for f in files:
        if os.path.isfile(source_path + "/" + f):
            try:
                shutil.copy2(source_path + "/" + f, target_path + f)
            except shutil.SameFileError:
                pass


def mangled_dirname(base_directory: str, prefix: str) -> str:
    MANGLER_LENGTH = 16
    dirs = []
    if os.path.isdir(base_directory):
        dirs = list(
            filter(lambda fn: fn.startswith(prefix), os.listdir(base_directory))
        )
    if dirs:
        assert len(dirs) == 1, f"Mutliple directories {base_directory}/{prefix}*"
        whole_path = os.path.join(base_directory, dirs[0])
        assert os.path.isdir(whole_path), f"Not directory: {whole_path}"
        return dirs[0]
    else:
        suffix = ''.join(
            random.choice(string.ascii_uppercase + string.digits
            + string.ascii_lowercase)
            for _ in range(MANGLER_LENGTH)
        )
        whole_path = os.path.join(base_directory, prefix+suffix)
        os.makedirs(whole_path)
        return prefix+suffix


def copy_data(task: model.Task, source_path: str, target_path: str) -> None:
    """Copy all data from repository to backend path."""
    if not os.path.isdir(target_path):
        os.makedirs(target_path)
    shutil.rmtree(target_path)
    if os.path.isdir(source_path):
        shutil.copytree(source_path, target_path)


def process_modules(task, git_path, replacement_metadata: Optional[ReplacementMetadata] = None):
    # Aktualni moduly v databazi
    modules = session.query(model.Module).\
        filter(model.Module.task == task.id).\
        order_by(model.Module.order).all()

    i = 0
    while (os.path.isdir(git_path + "/module" + str(i + 1))):
        if i < len(modules):
            module = modules[i]
            module.order = i
        else:
            module = model.Module(
                task=task.id,
                type="general",
                name="",
                order=i
            )
            session.add(module)
            session.commit()

        log("Processing module" + str(i + 1))
        process_module(module, git_path + "/module" + str(i + 1), task, replacement_metadata)

        try:
            session.commit()
        except BaseException:
            session.rollback()
            raise

        i += 1

    if i == 0:
        # No module -> no public evaluation
        global eval_public
        eval_public = False

    # Smazeme prebytecne moduly
    while i < len(modules):
        module = modules[i]
        try:
            session.delete(module)
            session.commit()
        except BaseException:
            session.rollback()
            raise

        i += 1


def process_module(module, module_path, task, replacement_metadata: Optional[ReplacementMetadata] = None):
    """Zpracovani modulu
    'module' je vzdy inicializovany
    'module'_path muze byt bez lomitka na konci
    """

    specific = process_module_json(module, module_path + "/module.json")

    # Copy whole module directory into data/modules
    log("Copying module data")
    target_path = os.path.join("data", "modules", str(module.id))
    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
    shutil.copytree(module_path, target_path)

    module.custom = os.path.isfile(os.path.join(target_path, "module-gen"))

    process_module_md(module, module_path + "/module.md", specific, task, replacement_metadata)


ModuleSpecs = Dict[str, Union[str, int, float, bool, None,
                              Dict[str, Union[str, int]]]]


def process_module_json(module: model.Module, filename: str) -> ModuleSpecs:
    """Zpracovani souboru module.json"""

    log("Processing module json")
    with open(filename, 'r', encoding='utf-8-sig') as f:
        data = json.loads(f.read())

    if data['type'] == 'text':
        module.type = model.ModuleType.TEXT
    elif data['type'] == 'general':
        module.type = model.ModuleType.GENERAL
    elif data['type'] == 'programming':
        module.type = model.ModuleType.PROGRAMMING
    elif data['type'] == 'quiz':
        module.type = model.ModuleType.QUIZ
    elif data['type'] == 'sortable':
        module.type = model.ModuleType.SORTABLE
    else:
        module.type = model.ModuleType.GENERAL

    # JSON parametry pro specificky typ modulu
    specific = data[data['type']] if data['type'] in data else {}

    module.max_points = data['max_points']
    module.autocorrect = data['autocorrect']
    module.bonus = data['bonus'] if 'bonus' in data else False
    module.action = data['action'] if 'action' in data else ""
    if isinstance(module.action, dict):
        module.action = json.dumps(module.action, indent=2, ensure_ascii=False)

    global eval_public
    if not module.autocorrect:
        eval_public = False

    return specific


def process_module_md(module, filename, specific, task, replacement_metadata: Optional[ReplacementMetadata] = None):
    """Zpracovani module.md
    Pandoc spoustime az uplne nakonec, abychom mohli provest analyzu souboru.
    """

    log("Processing module md")

    with open(filename, 'r') as f:
        data = f.readlines()

    # Hledame nazev modulu na nultem radku
    name = re.search(r"(# .*)", data[0])
    if name is not None:
        module.name = re.search(r"<h1(.*?)>(.*?)</h1>",
                                parse_pandoc(name.group(1))).group(2)
        data.pop(0)
    else:
        module.name = "Nazev modulu nenalezen"

    # Ukolem nasledujicich metod je zpracovat logiku modulu a v \data zanechat
    # uvodni text.
    if module.type == model.ModuleType.GENERAL:
        data = process_module_general(module, data, specific)
    elif module.type == model.ModuleType.PROGRAMMING:
        data = process_module_programming(module, data, specific,
                                          os.path.dirname(filename))
    elif module.type == model.ModuleType.QUIZ:
        data = process_module_quiz(module, data, specific, task)
    elif module.type == model.ModuleType.SORTABLE:
        data = process_module_sortable(module, data, specific)
    elif module.type == model.ModuleType.TEXT:
        data = process_module_text(module, data, specific,
                                   os.path.dirname(filename), task)
    else:
        module.description = "Neznamy typ modulu"

    log("Processing body")

    # Parsovani tela zadani
    module.description = parse_simple_text(task, ''.join(data), replacement_metadata)


def process_module_general(module: model.Module, lines: List[str],
                           specific: ModuleSpecs) -> List[str]:
    """Tady opravdu nema nic byt, general module nema zadnou logiku"""

    log("Processing general module")
    module.data = '{}'
    return lines


def process_module_programming(module: model.Module, lines: List[str],
                               specific: ModuleSpecs,
                               source_path: str) -> List[str]:
    log("Processing programming module")

    # Hledame vzorovy kod v zadani
    line = 0
    while (line < len(lines)) and (not re.match(r"^```~python", lines[line])):
        line += 1
    if line == len(lines):
        return lines

    # Hledame konec kodu
    end = line + 1
    while (end < len(lines)) and (not re.match(r"^```", lines[end])):
        end += 1

    code = ''.join(lines[line + 1:end])

    # Pridame vzorovy kod do \module.data
    data = {}
    data['programming'] = {}
    data['programming']['default_code'] = code
    if 'version' in specific:
        data['programming']['version'] = specific['version']

    target_path = os.path.join("data", "modules", str(module.id))
    data['programming']['merge_script'] = os.path.join(target_path, "merge")
    data['programming']['stdin'] = os.path.join(target_path, "stdin.txt")
    if not os.path.isfile(os.path.join(source_path, "/stdin.txt")):
        open(os.path.join(target_path, "stdin.txt"),
             "a").close()  # create empty stdin
    if os.path.isfile(os.path.join(source_path, "post")):
        data['programming']['post_trigger_script'] = os.path.join(target_path,
                                                                  "post")
    data['programming']['check_script'] = os.path.join(target_path, "eval")

    # direktivy z module.json
    if 'limits' in specific:
        data['programming']['limits'] = specific['limits']

    module.data = json.dumps(data, indent=2, ensure_ascii=False)
    return lines[:line]


def process_module_quiz(module, lines, specific, task, replacement_metadata: Optional[ReplacementMetadata] = None):
    log("Processing quiz module")

    # Hledame jednotlive otazky
    quiz_data = []
    line = 0
    text_end = 0
    while (line < len(lines)):
        while ((line < len(lines)) and
               (not re.match(r"^##(.*?) \(([rc])\)", lines[line]))):
            line += 1
        if text_end == 0:
            text_end = line
        if line == len(lines):
            break

        # Parsovani otazky
        question = {}
        head = re.match(r"^##(.*?) \(([rc])\)", lines[line])
        question['question'] = re.match("<p>(.*)</p>",
                                        parse_pandoc(head.group(1))).group(1)
        if head.group(2) == 'r':
            question['type'] = 'radio'
        else:
            question['type'] = 'checkbox'

        # Hledame pruvodni text otazky
        line += 1
        end = line
        while (end < len(lines)) and (not re.match(r"^~", lines[end])):
            end += 1
        question['text'] = parse_simple_text(task, ''.join(lines[line:end]), replacement_metadata)

        # Parsujeme mozne odpovedi
        line = end
        options = []
        correct = []
        while line < len(lines):
            match = re.match(r"^~\s*(.*?)\s*(\*|-)(\s|-)*$",
                             lines[line] + " -")
            if not match:
                break
            options.append(parse_pandoc(match.group(1)).replace("<p>", "").
                           replace("</p>", "").replace('\n', ''))
            if match.group(2) == '*':
                correct.append(len(options) - 1)

            line += 1

        question['options'] = options
        question['correct'] = correct

        # Pridame otazku
        quiz_data.append(question)

    module.data = json.dumps({'quiz': quiz_data}, indent=2, ensure_ascii=False)
    return lines[:text_end]


def process_module_sortable(module: model.Module,
                            lines: List[str],
                            specific: ModuleSpecs) -> List[str]:
    log("Processing sortable module")

    sort_data = {}
    sort_data['fixed'] = []
    sort_data['movable'] = []
    sort_data['correct'] = []

    line = 0
    while (line < len(lines)) and (not re.match(r"^~", lines[line])):
        line += 1
    text_end = line

    # Parsovani fixed casti
    while line < len(lines):
        match = re.match(r"^~\s*(.*)", lines[line])
        if not match:
            break
        parsed = parse_pandoc(match.group(1)).replace("<p>", "").\
            replace("</p>", "").replace('\n', '')
        sort_data['fixed'].append({
            'content': parsed,
            'offset': get_sortable_offset(parsed)
        })
        line += 1

    # Volny radek mezi fixed a movable casti
    line += 1

    # Movable cast
    while line < len(lines):
        match = re.match(r"^~\s*(.*)", lines[line])
        if not match:
            break
        parsed = parse_pandoc(match.group(1)).replace("<p>", "").\
            replace("</p>", "").replace('\n', '')
        sort_data['movable'].append({
            'content': parsed,
            'offset': get_sortable_offset(parsed)
        })
        line += 1

    # Parsovani spravnych poradi
    while line < len(lines):
        match = re.match(r"^\s*\((((a|b)\d+,)*(a|b)\d+)\)", lines[line])
        if match:
            sort_data['correct'].append(match.group(1).split(','))
        line += 1

    module.data = json.dumps({'sortable': sort_data}, indent=2, ensure_ascii=False)
    return lines[:text_end]


def get_sortable_offset(text: str) -> int:
    if re.match(r"^(if|Vstup:|while|for|def) ", text):
        return 1
    elif re.match(r"^(fi|od)$", text) or re.match(r"^return ", text):
        return -1
    return 0


def process_module_text(module, lines, specific, path, task, replacement_metadata: Optional[ReplacementMetadata] = None):
    log("Processing text module")

    text_data = {"inputs": 0}

    line = 0
    while (line < len(lines)) and (not re.match(r"^~", lines[line])):
        line += 1
    text_end = line
    if line >= len(lines):
        module.data = json.dumps(text_data, indent=2, ensure_ascii=False)
        return lines

    inputs_cnt = 0
    diff = []
    questions = []
    while line < len(lines):
        match = re.match(r"^~\s*(.*?)\s*(\*\*(.*?)\*\*)?\s*$", lines[line])
        if not match:
            break

        questions.append(parse_simple_text(task, match.group(1), replacement_metadata).
                         replace("<p>", "").replace("</p>", ""))

        inputs_cnt += 1
        if match.group(3):
            diff.append(match.group(3))
        else:
            if len(diff) > 0:
                diff.append("")

        line += 1

    text_data['questions'] = questions
    text_data['inputs'] = inputs_cnt
    if len(diff) > 0:
        text_data['diff'] = diff
    else:
        # Zkopirujeme eval skript
        target_path = "data/modules/" + str(module.id) + "/"
        if not os.path.isdir(target_path):
            os.makedirs(target_path)
        shutil.copy2(path + "/eval", target_path + "eval")
        text_data['eval_script'] = target_path + "eval"

    module.data = json.dumps({'text': text_data}, indent=2, ensure_ascii=False)
    return lines[:text_end]

###############################################################################
# Pomocne parsovaci funkce:


def parse_pandoc(source: str) -> str:
    r"""Parsovani stringu \source pandocem"""

    return pypandoc.convert_text(
        source,
        'html5',
        format='markdown+smart',
        extra_args=['--mathjax', '--email-obfuscation=none', '--wrap=none']
    )


def replace_h(source: str) -> str:
    """<h2> -> <h3>, <h3> -> <h4>, <h4> -> <h5> (to musi stacit)"""

    return source.replace("<h4", "<h5").replace("</h4>", "</h5>"). \
        replace("<h3", "<h4").replace("</h3>", "</h4>"). \
        replace("<h2", "<h3").replace("</h2>", "</h3>"). \
        replace("<h1", "<h3").replace("</h1>", "</h3>")


def one_ksi_pseudocode(match):
    r"""Stara se o vnitrek jednoho pseudokodu
    na vstup dostane \match, \match.group() obsahuje
    "<ksi-pseudocode>TEXT</ksi-pseudocode>".
    """

    source = match.group()
    source = re.sub(
        r"(function|funkce|procedure|Vstup|Výstup|then|return|else)",
        r"**\1**", source
    )

    # Za klicovym slovem musi nasledovat mezera
    source = re.sub(r"(if|while|for) ", r"**\1** ", source)

    # Pred klicovymslovem musi nasledovat mezera
    source = re.sub(r" (do)", r" **\1**", source)

    # Klicove slovo musi byt na samostatnem radku
    source = re.sub(r"\n(\s*)(od|fi)\s*(\\?)\n", r"\n\1**\2**\3\n", source)
    source = re.sub(r"<ksi-pseudocode>", r"<div style='padding-left:20px'>\n",
                    source)
    source = re.sub(r"</ksi-pseudocode>", r"</div>", source)

    # Takto donutime pandoc davat kazdy radek do samostateho odstavce
    source = re.sub(r"\n", r"\n\n", source)
    source = re.sub(r"(\t|    )", r"&emsp;", source)
    return source


def ksi_pseudocode(source):
    """Nahrazuje <ksi-pseudocode> za prislusne HTML"""

    source = re.sub("<ksi-pseudocode>\n((.|\n)*?)</ksi-pseudocode>",
                    one_ksi_pseudocode, source)
    return source


def one_ksi_collapse(match: re.Match, metadata: ReplacementMetadata) -> str:
    """Nahrauje jedno <ksi-collapse>"""
    metadata.collapse_max_id += 1
    collapse_id = metadata.collapse_max_id

    return """
<div class="panel panel-ksi panel-group">
<div class="panel-heading panel-heading-ksi"><h4 class="panel-title"><a data-toggle="collapse" href="#collapse""" \
           + str(collapse_id) + """">""" + match.group(1) + """</a></h4></div>
<div id="collapse""" + str(collapse_id) + """" class="panel-collapse collapse">
<div class="panel-body">"""


def ksi_collapse(source: str, replacement_metadata: Optional[ReplacementMetadata] = None) -> str:
    """Nahrazuje <ksi-collapse> za HTML plne silenych <div>u"""
    if replacement_metadata is None:
        replacement_metadata = ReplacementMetadata.get_default()

    source = re.sub(
        r"<ksi-collapse title=\"(.*?)\">",
        lambda match: one_ksi_collapse(match, replacement_metadata),
        source
    )
    return source.replace("</ksi-collapse>", "</div></div></div>")


def format_custom_tags(source: str) -> str:
    """
    Replaces all custom-defined tags with divs TODO: also support ksi-collapsible and ksi-pseudocode
    e.g. <ksi-tip> is replaced with <div class="ksi-custom ksi-tip">
    :param source: HTML to adjust
    :return: adjusted HTML
    """
    tags = ('ksi-tip',)
    for tag in tags:
        tag_escaped = re.escape(tag)
        source = re.sub(fr'<{tag_escaped}(.*?)>', fr'<div class="ksi-custom {tag}"\1>', source, flags=re.IGNORECASE)
        source = re.sub(fr'</{tag_escaped}>', r"</div>", source, flags=re.IGNORECASE)
    return source


def change_links(task: model.Task, source: str) -> str:
    """Nahrazuje odkazy do ../data/ a data/ za odkazy do backendu."""

    allowed_prefixes = ['(../', '(', '"']  # These should be mutually exclusive
    urls_to_replace = {
        "data_solution/": f"{util.config.backend_url()}/taskContent/{task.id}/{task.mangled_soldir}/",
        "data/": f"{util.config.backend_url()}/taskContent/{task.id}/{task.mangled_datadir}/"
    }

    res = source

    for url_fragment in urls_to_replace:
        for prefix in allowed_prefixes:
            res = res.replace(prefix + url_fragment, prefix + urls_to_replace[url_fragment])

    return res


def add_table_class(source: str) -> str:
    """Doplni ke kazde tabulce class="table table-striped"
    Tohleto bohuzel nejde udelat lip (napriklad explicitnim napsanim do
    markdownu).
    """

    return re.sub(r"<table>", "<table class='table table-striped'>", source)


def parse_simple_text(task, text: str, replacement_metadata: Optional[ReplacementMetadata] = None):
    return add_table_class(
        change_links(
            task, replace_h(
                parse_pandoc(
                    ksi_collapse(
                        ksi_pseudocode(
                            format_custom_tags(
                                text
                            )
                        ),
                        replacement_metadata
                    )
                )
            )
        )
    )

###############################################################################


def create_log(task: model.Task, status: str) -> None:
    with open(LOGFILE, 'w') as f:
        f.write(str(task.id) + '\n')


def log(text: str, syslog: bool = False, task: Optional[int] = None) -> None:
    if syslog:
        get_log().info(f"[DEPLOY] [{task}] {text}")
    with open(LOGFILE, 'a') as f:
        f.write(text + '\n')

###############################################################################
