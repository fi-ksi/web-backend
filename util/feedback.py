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
        'type': 'stars',
        'text': 'Jak dobře ti přišla úloha vysvětlená?',
    },
    {
        'id': 'interesting',
        'type': 'stars',
        'text': 'Jak moc ti přijde úloha zajímavá?',
    },
    {
        'id': 'difficult',
        'type': 'line',
        'text': 'Jak moc ti přijde úloha těžká?',
    },
    {
        'id': 'comment',
        'type': 'text_large',
        'text': ('Chceš nám vzkázat něco, co nám pomůže příště úlohu připravit '
                 'lépe? (nepovinné)'),
    },
]

MAX_CATEGORIES = 16
MAX_ID_LEN = 32
MAX_TYPE_LEN = 32
MAX_QUESTION_LEN = 1024
MAX_ANSWER_LEN = 8192

ALLOWED_TYPES = ['stars', 'line', 'comment']
TYPE_TO_TYPE = {
    'stars': int,
    'line': int,
    'comment': str,
}


class EForbiddenType(Exception):
    pass


class EUnmatchingDataType(Exception):
    pass


class EMissingAnswer(Exception):
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
            catgegory['answer'] = category['answer'][:MAX_ANSWER_LEN]

        if category['type'] not in ALLOWED_TYPES:
            raise EUnmatchingDataType(
                "'%s' is not allowed as question type!" % (category['type'])
            )

        if not isinstance(category['answer'], TYPE_TO_TYPE[category['type']]):
            raise EForbiddenType(
                "'%s' is not allowed as answer of type '%s'!" % (
                    type(category['answer']).__name__, category['type']
                )
            )

        to_store.append({
            'id': category['id'][:MAX_ID_LEN],
            'type': category['type'][:MAX_TYPE_LEN],
            'text': category['text'][:MAX_QUESTION_LEN],
            'answer': category['answer'],
        })

    return to_store


def empty_to_json(task_id, user_id):
    return {
        'taskId': task_id,
        'userId': user_id,
        'categories': CATEGORIES,
        'filled': False,
    }


def to_json(feedback):
    return {
        'taskId': feedback.task,
        'userId': feedback.user,
        'lastUpdated': feedback.lastUpdated.isoformat(),
        'categories': json.loads(feedback.content),
        'filled': True,
    }
