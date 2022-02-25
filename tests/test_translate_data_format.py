from importlib import resources

import intake
import pytest
import xarray as xr

from ldndctools.io.xmlwriter import translate_data_format
from ldndctools.misc.types import LayerData, RES
from ldndctools.sources.soil.soil_iscricwise import ISRICWISE_SoilDataset


@pytest.fixture
def soil():
    """return lr soil data"""
    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    soil = catalog.soil(res=RES.LR.name).read()
    return ISRICWISE_SoilDataset(soil)


@pytest.fixture
def soil_location(soil):
    """return a sample location of lr soil data"""
    sample_points = soil.data.sel(
        lat=xr.DataArray([47.49], dims="points"),
        lon=xr.DataArray([11.10], dims="points"),
        method="nearest",
    )
    return sample_points.sel(points=0)


def test_translate_data_format_return_type(soil_location):
    assert isinstance(translate_data_format(soil_location)[0], LayerData) is True
