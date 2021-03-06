from db import session
import model
import util
from collections import namedtuple
import re
import json


FeedbackId = namedtuple('FeedbackId', ['user', 'task'])

CATEGORIES = [
    {
        'id': 'explained',
        'ftype': 'stars',
        'text': 'Jak dobře ti přišla úloha vysvětlená?',
    },
    {
        'id': 'interesting',
        'ftype': 'stars',
        'text': 'Jak moc ti přijde úloha zajímavá?',
    },
    {
        'id': 'difficult',
        'ftype': 'line',
        'text': 'Jak moc ti přijde úloha těžká?',
    },
    {
        'id': 'comment',
        'ftype': 'text_large',
        'text': ('Chceš nám vzkázat něco, co nám pomůže příště úlohu připravit '
                 'lépe? (nepovinné)'),
    },
]

MAX_CATEGORIES = 16
MAX_ID_LEN = 32
MAX_TYPE_LEN = 32
MAX_QUESTION_LEN = 1024
MAX_ANSWER_LEN = 8192

ALLOWED_TYPES = ['stars', 'line', 'text_large']
TYPE_TO_TYPE = {
    'stars': int,
    'line': int,
    'text_large': str,
}
ALLOWED_RANGES = {
    'stars': range(0, 6),
    'line': range(0, 6),
}

class EForbiddenType(Exception):
    pass


class EUnmatchingDataType(Exception):
    pass


class EMissingAnswer(Exception):
    pass


class EOutOfRange(Exception):
    pass


def parse_feedback(categories):
    # Limit number of categories
    categoriess = categories[:MAX_CATEGORIES]

    # Check input for validity
    ids = set()
    to_store = []
    for category in categories:
        if category['id'][:MAX_ID_LEN] in ids:
            continue
        ids.add(category['id'][:MAX_ID_LEN])

        if 'answer' not in category:
            raise EMissingAnswer(
                "Missing answer for question '%s'" % (category['id'])
            )

        if isinstance(category['answer'], str):
            category['answer'] = category['answer'][:MAX_ANSWER_LEN]

        if category['ftype'] not in ALLOWED_TYPES:
            raise EUnmatchingDataType(
                "'%s' is not allowed as question type!" % (category['ftype'])
            )

        if not isinstance(category['answer'], TYPE_TO_TYPE[category['ftype']]):
            raise EForbiddenType(
                "'%s' is not allowed as answer of type '%s'!" % (
                    type(category['answer']).__name__, category['ftype']
                )
            )

        if category['ftype'] in ALLOWED_RANGES and \
           category['answer'] not in ALLOWED_RANGES[category['ftype']]:
           raise EOutOfRange("'%s' out of range!" % (category['id']))

        to_store.append({
            'id': category['id'][:MAX_ID_LEN],
            'ftype': category['ftype'][:MAX_TYPE_LEN],
            'text': category['text'][:MAX_QUESTION_LEN],
            'answer': category['answer'],
        })

    return to_store


def empty_to_json(task_id, user_id):
    return {
        'id': task_id,
        'userId': user_id,
        'categories': CATEGORIES,
        'filled': False,
    }


def to_json(feedback):
    return {
        'id': feedback.task,
        'userId': feedback.user,
        'lastUpdated': feedback.lastUpdated.isoformat(),
        'categories': json.loads(feedback.content),
        'filled': True,
    }
