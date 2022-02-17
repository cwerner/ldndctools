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

    def test_convert_inverse(self):
        assert convert_unit("percent", "fraction") == 0.01

    def test_convert_invalid(self):
        with pytest.raises(NotImplementedError):
            assert convert_unit("percent", "g cm-3")


@pytest.mark.usefixtures(
    "source_attribs", "target_attribs", "converter", "fake_isricwise"
)
class TestConverter:
    def test_raise_for_dataset(self, converter, fake_isricwise):
        with pytest.raises(NotImplementedError):
            converter(fake_isricwise)

    def test_specified_name_after_conversion(self, converter, fake_isricwise):
        da = converter(fake_isricwise.original["BULK"], var="BULK")
        assert da.name == "bd"

    def test_unspecified_name_after_conversion(self, converter, fake_isricwise):
        da = converter(fake_isricwise.original["CLPC"])
        assert da.name == "clay"

    def test_conversion_units(self, converter, fake_isricwise):
        da = converter(fake_isricwise.original["CLPC"])
        assert_equal(fake_isricwise.original["CLPC"], da * 100)

        da = converter(fake_isricwise.original["PHAQ"])
        assert_equal(fake_isricwise.original["PHAQ"], da * 1)

        da = converter(fake_isricwise.original["BULK"])
        assert_equal(fake_isricwise.original["BULK"], da * 1)
