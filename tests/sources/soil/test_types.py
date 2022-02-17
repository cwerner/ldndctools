from dataclasses import fields

from ldndctools.sources.soil.types import BaseAttribute, FullAttribute


def test_attrib_fieldnames():
    assert {x.name for x in fields(BaseAttribute)} == {"name", "unit"}
    assert {x.name for x in fields(FullAttribute)} == {
        "name",
        "long_name",
        "unit",
        "msd",
    }
