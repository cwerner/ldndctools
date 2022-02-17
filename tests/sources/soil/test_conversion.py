import pytest
from xarray.testing import assert_equal

from ldndctools.sources.soil.conversion import convert_unit, Converter


@pytest.fixture()
def converter(source_attribs, target_attribs):
    return Converter(
        source_attribs,
        target_attribs,
        mapper={"BULK": "bd", "PHAQ": "ph", "CLPC": "clay"},
    )


class TestConvertUnit:
    def test_convert_regular(self):
        assert convert_unit("fraction", "percent") == 100
        assert convert_unit("mm", "cm") == 10

    def test_convert_inverse(self):
        assert convert_unit("percent", "fraction") == 0.01
        assert convert_unit("cm", "mm") == 0.1

    def test_convert_invalid(self):
        with pytest.raises(NotImplementedError):
            assert convert_unit("percent", "g cm-3")


@pytest.mark.skip(reason="[REWRITE] This check is no good")
@pytest.mark.usefixtures(
    "source_attribs", "target_attribs", "converter", "isricwise_ds"
)
class TestConverter:
    def test_raise_for_dataset(self, converter, isricwise_ds):
        with pytest.raises(NotImplementedError):
            converter(isricwise_ds)

    def test_specified_name_after_conversion(self, converter, isricwise_ds):
        da = converter(isricwise_ds.original["BULK"], var="BULK")
        assert da.name == "bd"

    def test_unspecified_name_after_conversion(self, converter, isricwise_ds):
        da = converter(isricwise_ds.original["CLPC"])
        assert da.name == "clay"

    def test_conversion_units(self, converter, isricwise_ds):
        source = isricwise_ds.original["CLPC"] * isricwise_ds.mask_3d

        da = converter(source)
        assert_equal(source, da * 0.01)

        # da = converter(isricwise_ds.original["PHAQ"])
        # assert_equal(isricwise_ds.original["PHAQ"], da * 1)

        # da = converter(isricwise_ds.original["BULK"])
        # assert_equal(isricwise_ds.original["BULK"], da * 1)
