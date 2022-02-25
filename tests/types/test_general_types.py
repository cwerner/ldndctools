import pytest
from pydantic import ValidationError

from ldndctools.misc.types import BoundingBox, LayerData


@pytest.fixture
def layer_data():
    return LayerData()


@pytest.fixture
def layer_data_fields():
    flds = (
        "depth,split,ph,scel,bd,sks,norg,corg,clay,wcmin,wcmax,sand,silt,iron,topd,botd"
    )
    return set(flds.split(","))


def test_bounding_box_valid_ranges():
    with pytest.raises(ValidationError):
        BoundingBox(x1=-181, x2=180, y1=-20, y2=20)

    with pytest.raises(ValidationError):
        BoundingBox(x1=-180, x2=185, y1=-20, y2=20)

    with pytest.raises(ValidationError):
        BoundingBox(x1=-180, x2=180, y1=-100, y2=20)

    with pytest.raises(ValidationError):
        BoundingBox(x1=-180, x2=180, y1=-20, y2=120)

    with pytest.raises(ValidationError):
        BoundingBox(x1=-185, x2=181, y1=-120, y2=120)


def test_bounding_box_plausible_coords():
    with pytest.raises(ValidationError):
        BoundingBox(x1=-140, x2=-150, y1=-20, y2=20)

    with pytest.raises(ValidationError):
        BoundingBox(x1=-180, x2=-180, y1=20, y2=-20)


def test_bounding_box_invalid_assignment():
    with pytest.raises(ValidationError):
        bbox = BoundingBox()
        bbox.x1 = -200


def test_bounding_box_invalid_assignment_x1_greater_x2():
    with pytest.raises(ValidationError):
        bbox = BoundingBox()
        bbox.x2 = -200


def test_layer_data_json_does_not_contain_null(layer_data):
    assert "null" not in layer_data.json()


def test_layer_data_serialize_does_not_contain_null(layer_data):
    assert None not in layer_data.serialize().values()


def test_layer_data_serialize_returns_dict_with_number_values(layer_data):
    assert type(layer_data.serialize()) == dict
    assert all([isinstance(x, str) for x in layer_data.serialize().values()])


def test_layer_data_contains_all_fields(layer_data, layer_data_fields):
    fields = {k for k in layer_data.__annotations__.keys()}
    assert fields == layer_data_fields


def test_layer_data_raise_validation_error_out_of_range_value(layer_data):
    with pytest.raises(ValidationError):
        layer_data.sand = 110


@pytest.mark.skip(
    reason="[REWRITE] This check is currently not activated (wcmin := None)"
)
def test_layer_data_raise_validation_error_wcmin_wcmax_check_init():
    with pytest.raises(ValidationError):
        LayerData(wcmin=100, wcmax=50)


# this should also raise, however assignments are not root_validated ?!?
@pytest.mark.skip(
    reason="[REWRITE] This check is currently not activated (wcmin := None)"
)
def test_layer_data_raise_validation_error_wcmin_wcmax_check_assignment(layer_data):
    with pytest.raises(ValidationError):
        layer_data.wcmin = 100
        layer_data.wcmax = 50


def test_layer_data_raise_validation_error_texture_check(layer_data):
    with pytest.raises(ValidationError):
        layer_data.sand = 10
        layer_data.silt = 40
        layer_data.clay = 60

    with pytest.raises(ValidationError):
        layer_data.sand = 30
        layer_data.silt = 90
