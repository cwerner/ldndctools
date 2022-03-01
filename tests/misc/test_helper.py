from typing import Optional

import pytest

from ldndctools.misc.helper import mutually_exclusive


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
