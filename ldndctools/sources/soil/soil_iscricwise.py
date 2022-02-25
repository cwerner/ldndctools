from itertools import takewhile
from typing import Dict, Iterable, Optional

import xarray as xr

from ldndctools.sources.soil.conversion import Converter
from ldndctools.sources.soil.soil_base import SoilDataset
from ldndctools.sources.soil.types import BaseAttribute

__all__ = ["ISRICWISE_SoilDataset"]


def count_layers(x):
    """sum valid values until condition a>=0 is not true any more"""
    return sum([1 for _ in takewhile(lambda a: a >= 0, x)])


class ISRICWISE_SoilDataset(SoilDataset):
    _source_attrs: Iterable[BaseAttribute] = [
        BaseAttribute(name="DEPTH", unit="cm"),
        BaseAttribute(name="BULK", unit="g cm-3"),
        BaseAttribute(name="PHAQ", unit="-"),
        BaseAttribute(name="CLPC", unit="percent"),
        BaseAttribute(name="SDTO", unit="percent"),
        BaseAttribute(name="STPC", unit="percent"),
        BaseAttribute(name="TOTC", unit="g kg-1"),
        BaseAttribute(name="TOTN", unit="g kg-1"),
        BaseAttribute(name="CFRAG", unit="percent"),
    ]

    _mapper: Dict[str, str] = {
        "BULK": "bd",
        "DEPTH": "depth",
        "PHAQ": "ph",
        "CLPC": "clay",
        "SDTO": "sand",
        "STPC": "silt",
        "TOTC": "corg",
        "TOTN": "norg",
        "CFRAG": "scel",
    }

    def __init__(self, soildata: xr.Dataset, *, zdim: Optional[str] = "lev"):
        self._zdim = zdim
        self._soil = self._calculate_missing_vars(soildata)
        self._mask = self._build_mask(self._soil)

    def _calculate_missing_vars(self, soildata: xr.Dataset) -> xr.Dataset:
        """calculate missing soil variables (i.e. depth)"""
        if set(["BotDep", "TopDep"]).issubset(soildata.data_vars):
            depth = soildata["BotDep"] - soildata["TopDep"]
            soildata["DEPTH"] = depth.where(depth > 0)
        else:
            raise ValueError("Required variables not in dataset")
        return soildata

    def _build_mask(self, soildata: xr.Dataset) -> xr.DataArray:
        """build a mask based on missing soil attributes"""
        check_vars = ["PHAQ", "BULK", "CLPC", "DEPTH"]

        ds_mask = xr.Dataset()
        for v in [cv for cv in soildata.data_vars if cv in check_vars]:
            ds_mask[v] = xr.apply_ufunc(
                count_layers,
                soildata[v],
                input_core_dims=[[self._zdim]],
                vectorize=True,
            )
            ds_mask[v] = ds_mask[v].where(ds_mask[v] > 0)
        return ds_mask.to_array(dim="v", name="mask").min(dim="v", skipna=False)

    def _converter(self) -> Converter:
        return Converter(
            self._source_attrs, SoilDataset._target_attrs, mapper=self._mapper
        )
