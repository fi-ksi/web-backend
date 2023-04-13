from typing import Optional, Tuple, TypedDict

from db import session
import model
from util import config
import util


class Year(TypedDict):
    id: int
    index: int
    year: str
    sum_points: float
    tasks_cnt: int
    sealed: bool
    point_pad: float


def to_json(year: model.Year,
            sum_points: Optional[Tuple[float, int]] = None) -> Year:
    if sum_points is None:
        sum_points = util.task.max_points_year_dict()[year.id]

    return {
        'id': year.id,
        'index': year.id,
        'year': year.year,
        'sum_points': sum_points[0],
        'tasks_cnt': int(sum_points[1]),
        'sealed': year.sealed,
        'point_pad': year.point_pad
    }


def year_end(year: model.Year) -> int:
    return int(year.year.replace(" ", "").split("/")[0]) + 1
