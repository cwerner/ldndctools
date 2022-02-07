from importlib import resources

import intake
import pytest
import xarray as xr

from ldndctools.io.xmlwriter import translate_data_format
from ldndctools.misc.types import RES, LayerData


@pytest.fixture
def soil():
    """return lr soil data"""
    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    return catalog.soil(res=RES.LR.name).read()


@pytest.fixture
def soil_location(soil):
    """return a sample location of lr soil data"""
    sample_points = soil.sel(
        lat=xr.DataArray([47.49], dims="points"),
        lon=xr.DataArray([11.10], dims="points"),
        method="nearest",
    )

    sample_point = sample_points.sel(points=0)
    return sample_point


def test_translate_data_format_return_type(soil_location):
    assert isinstance(translate_data_format(soil_location)[0], LayerData) is True
