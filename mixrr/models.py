from dataclasses import dataclass
from typing import Optional, Tuple


Camelot = Tuple[int, str]


@dataclass
class Track:
    id: str
    name: str
    artists: str
    camelot: Camelot
    camelot_str: str
    bpm: float
    url: str
    jump: bool = False
