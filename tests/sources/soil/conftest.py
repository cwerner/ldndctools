import pytest
import xarray as xr

from ldndctools.sources.soil.soil_iscricwise import ISRICWISE_SoilDataset
from ldndctools.sources.soil.types import BaseAttribute, FullAttribute


@pytest.fixture()
def source_attribs():
    return [
        BaseAttribute(name="BULK", unit="g cm-3"),
        BaseAttribute(name="PHAQ", unit="-"),
        BaseAttribute(name="CLPC", unit="percent"),
    ]


@pytest.fixture()
def target_attribs():
    return [
        FullAttribute(name="bd", long_name="bulk density", unit="g cm-3", msd=2),
        FullAttribute(name="ph", long_name="pH", unit="-", msd=2),
        FullAttribute(name="clay", long_name="clay fraction", unit="fraction", msd=4),
    ]


@pytest.fixture()
def fake_isricwise():
    ph = [
        [[-1, 7.4, 5.2], [5.2, 6.5, 5.1], [-1, 6.2, 5.0]],
        [[-1, 7.6, 5.3], [5.5, 6.6, -1], [-1, 6.5, 5.3]],
        [[-1, 7.4, 5.2], [2.2, 6.8, -1], [-1, 6.4, -1]],
    ]

    cl = [
        [[-1, 0.30, 0.10], [0.1, 0.22, 0.1], [-1, 0.1, 0.15]],
        [[-1, 0.31, 0.09], [0.1, 0.16, 0.05], [-1, 0.11, 0.13]],
        [[-1, 0.29, 0.02], [0.05, 0.2, 0.2], [-1, 0.3, -1]],
    ]

    # NOTE: bd has one cell with valid data, but other vars are missing!
    bd = [
        [[0.5, 0.9, 0.95], [1.4, 1.3, 1.4], [-1, 1.6, 1.5]],
        [[0.8, 0.95, 1.05], [1.3, 1.25, 1.35], [-1, 1.7, 1.85]],
        [[0.6, 1.20, 1.3], [1.25, 1.45, 1.5], [-1, 1.65, -1]],
    ]

    coords = [("lev", [1, 2, 3]), ("lat", [0, 1, 2]), ("lon", [0, 1, 2])]
    ds = xr.Dataset()
    ds["PHAQ"] = xr.DataArray(ph, coords=coords)
    ds["CLPC"] = xr.DataArray(cl, coords=coords)
    ds["BULK"] = xr.DataArray(bd, coords=coords)

    return ISRICWISE_SoilDataset(ds, zdim="lev")
