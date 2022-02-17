from typing import Dict, Iterable, Optional, Union

import xarray as xr

from ldndctools.sources.soil.types import BaseAttribute, FullAttribute


def convert_unit(unit_a: str, unit_b: str) -> float:
    conversions = {
        ("fraction", "percent"): 100,
        ("g kg-1", "percent"): 1000,
    }

    if unit_a == unit_b:
        return 1

    for (a, b), c in conversions.items():
        if unit_a == a and unit_b == b:
            conv = c
            break
        elif unit_a == b and unit_b == a:
            conv = 1 / c
            break
    else:
        raise NotImplementedError(f"Conversion {unit_a}->{unit_b} not implemented")

    return conv


class Converter:
    def __init__(
        self,
        a: Iterable[Union[BaseAttribute, FullAttribute]],
        b: Iterable[FullAttribute],
        *,
        mapper: Dict[str, str],
    ):
        self._a = a
        self._b = b
        self._mapper = mapper

    def __call__(
        self, source_data: Union[xr.Dataset, xr.DataArray], *, var: Optional[str] = None
    ):
        if isinstance(source_data, xr.DataArray):
            if not var:
                var = source_data.name
        else:
            raise NotImplementedError("An xarray dataarray is required for source_data")

        source = next((x for x in self._a if x.name == var), None)
        target = next((x for x in self._b if x.name == self._mapper[var]), None)

        conv = convert_unit(source.unit, target.unit)

        target_data = source_data.copy() * conv
        target_data.name = target.name
        target_data.attrs["long_name"] = target.long_name
        target_data.attrs["unit"] = target.unit
        return target_data
