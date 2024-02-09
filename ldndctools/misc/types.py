import json
from enum import Enum
from typing import Optional

from pydantic import BaseModel, confloat, conint, model_validator, ValidationError
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder


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


class ValidationConfig:
    validate_assignment = True


@dataclass(config=ValidationConfig)
class BoundingBox:
    x1: confloat(ge=-180, le=180) = -180
    x2: confloat(ge=-180, le=180) = 180
    y1: confloat(ge=-90, le=90) = -90
    y2: confloat(ge=-90, le=90) = 90

    @model_validator(mode='after')
    def check_x1_smaller_x2(cls, values):
        if values.x1 >= values.x2:
            raise ValidationError("x1 must be smaller x2")
        return values

    @model_validator(mode='after')
    def check_y1_smaller_y2(cls, values):
        if values.y1 >= values.y2:
            raise ValidationError("y1 must be smaller y2")
        return values


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


class LayerData(BaseModel):
    depth: conint(gt=0) = 20
    split: Optional[conint(ge=0)] = None
    ph: Optional[confloat(ge=2.5, le=10.0)] = None
    scel: Optional[
        confloat(ge=0.0, lt=1.0)
    ] = None  # TODO: check that range 0...100 is correct
    bd: Optional[confloat(ge=0.3, le=2.65)] = None
    sks: Optional[confloat(ge=0.0)] = None
    norg: Optional[confloat(gt=0.0)] = None
    corg: Optional[confloat(gt=0.0)] = None
    clay: Optional[confloat(ge=0.0, lt=1.0)] = None
    sand: Optional[confloat(ge=0.0, lt=1.0)] = None
    silt: Optional[confloat(ge=0.0, lt=1.0)] = None
    wcmin: Optional[confloat(ge=0.0)] = None
    wcmax: Optional[confloat(ge=0.0)] = None
    iron: Optional[confloat(ge=0.0)] = None
    topd: Optional[conint(ge=-1)] = None
    botd: Optional[conint(ge=-1)] = None

    class Config:
        validate_assignment = True

    # @model_validator
    # def check_wcmin_smaller_wcmax(cls, values):
    #     wcmin, wcmax = values.get("wcmin"), values.get("wcmax")
    #     if None not in [wcmin, wcmax]:
    #         if wcmin >= wcmax:
    #             raise ValidationError("wcmin must be smaller wcmax")
    #     return values

    #@model_validator(mode='after')
    def check_texture_is_plausible(cls, values):
        sand, silt, clay = values.get("sand"), values.get("silt"), values.get("clay")
        args = [a for a in [sand, silt, clay] if a is not None]
        if args:
            if sum(args) > 1.0:
                raise ValidationError("sum(sand, silt, clay) > 100")
        return values

    def json(cls):
        """custom json() function that also replaces None with NODATA"""
        return json.dumps(cls, indent=2, default=pydantic_encoder).replace(
            "null", str(NODATA)
        )

    def serialize(cls, ignore=["topd", "botd", "split"]):
        """serialize data in ldndc layer conform format"""

        # format significant digits
        def _format(var: str, value: float) -> str:
            k, _, significant = tuple(zip(*nmap.values()))
            Ddigits = dict(zip(k, significant))
            if var in Ddigits:
                return str(round(value, Ddigits[var]))
            elif var in ["wcmin", "wcmax"]:
                return str(round(value, 2))
            return str(value)

        data = json.loads(
            json.dumps(cls, indent=2, default=pydantic_encoder).replace(
                "null", str(NODATA)
            )
        )
        return {k: _format(k, v) for k, v in data.items() if k not in ignore}
