from db import session
import model
import util
from typing import TypedDict, Tuple, Optional


class Wave(TypedDict):
    id: int
    year: int
    index: int
    caption: str
    garant: int
    time_published: str
    public: bool
    sum_points: float
    tasks_cnt: int


def to_json(wave: model.Wave,
            sum_points: Optional[Tuple[float, int]] = None) -> Wave:
    if sum_points is None:
        sum_points = util.task.max_points_wave_dict()[wave.id]

    return {
        'id': wave.id,
        'year': wave.year,
        'index': wave.index,
        'caption': wave.caption,
        'garant': wave.garant,
        'time_published': wave.time_published.isoformat(),
        'public': wave.public,
        'sum_points': sum_points[0],
        'tasks_cnt': sum_points[1]
    }
