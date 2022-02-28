import os

import geopandas as gpd
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
def isricwise_ds():
    # currently only using LR
    test_files = [
        os.path.join(os.path.dirname(__file__), p)
        for p in ["data/ISRICWISE_DE_LR.nc", "data/ISRICWISE_DE_HR.nc"]
    ]

    ds = xr.open_dataset(test_files[0])
    return ISRICWISE_SoilDataset(ds)


@pytest.fixture()
def country_gdf():
    test_files = [
        os.path.join(os.path.dirname(__file__), p)
        for p in ["data/ne_10m_admin_0_countries.zip"]
    ]
    return gpd.read_file(test_files[0])
