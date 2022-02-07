import pytest

from ldndctools.misc.types import LayerData


@pytest.fixture
def layer_data():
    return LayerData()


@pytest.fixture
def layer_data_items():
    return set(
        "depth,split,ph,scel,bd,sks,norg,corg,clay,wcmin,wcmax,sand,silt,iron".split(
            ","
        )
    )


def test_layerdata_fields(layer_data, layer_data_items):
    fields = {k for k in layer_data.__annotations__.keys()}
    assert fields == layer_data_items


def test_layerdata_as_dict(layer_data, layer_data_items):
    print(layer_data.as_dict())
    assert layer_data.as_dict().keys() == layer_data_items
