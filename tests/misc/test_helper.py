import xml.etree.cElementTree as et
from typing import Optional

import pytest

from ldndctools.misc.helper import dataset_to_bytes, mutually_exclusive, prettify


def test_mutually_exclusive_illegal_raises_typeerror():
    @mutually_exclusive("arg1", "arg2", "arg3")
    def dummy_function(
        arg1: Optional[str] = None,
        arg2: Optional[int] = None,
        arg3: Optional[bool] = None,
    ):
        return True

    with pytest.raises(TypeError):
        dummy_function(arg1="asf123", arg2=12)


def test_mutually_exclusive_for_some_args():
    @mutually_exclusive("arg1", "arg2")
    def dummy_function(
        arg1: Optional[str] = None,
        arg2: Optional[int] = None,
        arg3: Optional[bool] = None,
    ):
        return True

    assert dummy_function(arg1="asf123", arg3=True) is True


def test_mutually_exclusive_ignores_positional_arg():
    @mutually_exclusive("pos", "arg1", "arg2")
    def dummy_function(
        pos: int,
        arg1: Optional[str] = None,
        arg2: Optional[int] = None,
        arg3: Optional[bool] = None,
    ):
        return True

    # NOTE: positional arguments are ignored!
    assert dummy_function(12, arg1="asf123") is True


@pytest.fixture
def soildata(isricwise_ds):
    return isricwise_ds.data


def test_dataset_to_bytes(soildata):

    assert type(dataset_to_bytes(soildata)) == bytes


def test_prettify():
    e = et.Element("dummy_element")
    et.SubElement(e, "sub_element1", attrib={"a": "1", "b": "2"})
    se = et.SubElement(e, "sub_element2", attrib={"a": "3"})
    et.SubElement(se, "sub_sub_element1", attrib={"c": "abc"})

    res = """<?xml version="1.0" ?>
<dummy_element>
  <sub_element1 a="1" b="2"/>
  <sub_element2 a="3">
    <sub_sub_element1 c="abc"/>
  </sub_element2>
</dummy_element>
"""

    assert prettify(e) == res
