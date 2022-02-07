from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Optional


class BetterEnum(Enum):
    """a better enum type that also allows checking for members"""

    @classmethod
    def contains(cls, name):
        return name in cls.__members__

    @classmethod
    def names(cls):
        return [x for x in cls.__members__]

    @classmethod
    def members(cls):
        return [x for x in cls]


class RES(BetterEnum):
    LR = "Low-res [0.5°]"
    MR = "Medium-res [0.25°]"
    HR = "High-res [0.083°]"


@dataclass
class BoundingBox:
    x1: float = -180
    x2: float = 180
    y1: float = -90
    y2: float = 90


NODATA = -99.99


# map from isiric-wise fields and units to ldndc
# ldndcname, conversion, significant digits
nmap = {
    "TOTC": ("corg", 0.001, 5),
    "TOTN": ("norg", 0.001, 6),
    "PHAQ": ("ph", 1, 2),
    "BULK": ("bd", 1, 2),
    "CFRAG": ("scel", 0.01, 2),
    "SDTO": ("sand", 0.01, 2),
    "STPC": ("silt", 0.01, 2),
    "CLPC": ("clay", 0.01, 2),
    "TopDep": ("topd", 1, 0),
    "BotDep": ("botd", 1, 0),
}


@dataclass
class LayerData:
    depth: int = -1
    split: int = -1
    ph: float = NODATA
    scel: float = NODATA
    bd: float = NODATA
    sks: float = NODATA
    norg: float = NODATA
    corg: float = NODATA
    clay: float = NODATA
    wcmin: float = NODATA
    wcmax: float = NODATA
    sand: float = NODATA
    silt: float = NODATA
    iron: float = NODATA

    def as_dict(self, ignore: Optional[Iterable[str]] = None) -> Dict[str, str]:
        precision = dict((x[0], x[2]) for x in nmap.values())
        precision["depth"] = 0
        precision["split"] = 0
        precision["wcmin"] = 1
        precision["wcmax"] = 1
        precision["sks"] = 2
        precision["iron"] = 5

        out = {}
        for field, field_type in self.__annotations__.items():
            value = getattr(self, field)
            if field == NODATA:
                out[field] = f"{value:.2f}"
            elif isinstance(field_type, int):
                out[field] = str(value)
            else:
                out[field] = f"{value:.{precision[field]}f}"

        if ignore:
            for key in ignore:
                out.pop(key, None)

        return out
