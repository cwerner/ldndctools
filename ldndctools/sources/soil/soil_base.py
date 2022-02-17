from abc import ABC, abstractmethod

import xarray as xr

from ldndctools.sources.soil.types import FullAttribute

__all__ = []


class SoilDataset(ABC):
    required_attributes = ["_source_attrs", "_mapper"]

    _target_attrs = [
        FullAttribute(name="bd", long_name="bulk density", unit="g cm-3", msd=2),
        FullAttribute(name="depth", long_name="layer depth", unit="mm", msd=0),
        FullAttribute(name="corg", long_name="organic carbon", unit="g kg-1", msd=5),
        FullAttribute(name="norg", long_name="organic nitrogen", unit="g kg-1", msd=6),
        FullAttribute(name="ph", long_name="pH", unit="-", msd=2),
        FullAttribute(name="clay", long_name="clay fraction", unit="fraction", msd=2),
        FullAttribute(name="sand", long_name="sand fraction", unit="fraction", msd=2),
        FullAttribute(name="silt", long_name="silt fraction", unit="fraction", msd=2),
        FullAttribute(name="sks", long_name="unknown", unit="unknown", msd=1),
        FullAttribute(name="scel", long_name="coarse fraction", unit="fraction", msd=2),
        FullAttribute(name="wcmin", long_name="wcmin", unit="unknown", msd=1),
        FullAttribute(name="wcmax", long_name="wcmax", unit="unknown", msd=1),
    ]

    core_soil_attrs = ["bd", "clay", "sand", "corg", "norg"]

    def __init_subclass__(cls, **kwargs):
        for attr_name in cls.required_attributes:
            if not hasattr(cls, attr_name):
                raise NotImplementedError(f"Defining {attr_name} is required")
        return super().__init_subclass__(**kwargs)

    @abstractmethod
    def _build_mask(self, soildata: xr.Dataset) -> xr.Dataset:
        pass

    @abstractmethod
    def _converter(self):
        pass

    @property
    def mask(self):
        """return binary mask"""
        return (
            xr.ones_like(self._mask).where(self._mask >= 1)
            if self._mask is not None
            else None
        )

    @property
    def layer_mask(self):
        """return mask with indicators for number of layers"""
        return self._mask

    @property
    def original(self):
        """return source xarray dataset"""
        return self._soil if self._soil is not None else None

    @property
    def data(self):
        """return xarray dataset with ldndc standard variables"""
        if self.original is not None:
            ds = xr.Dataset()
            for var in self.original.data_vars:
                da = self._converter()(self.original[var])
                ds[da.name] = da
            return ds
        return None
