import pytest

from ldndctools.misc.errors import ParameterMissingError
from ldndctools.misc.types import LayerData
from ldndctools.misc.xmlclasses import calc_hydraulic_properties


def test_basic_computation():
    ld = LayerData(sand=0.1, clay=0.3, corg=0.05, bd=1.2)
    ld = calc_hydraulic_properties(ld)
    assert ld.wcmin == pytest.approx(295.35934)
    assert ld.wcmax == pytest.approx(472.21525)


def test_raise_for_missing_parameter():
    ld = LayerData(sand=0.1, clay=0.3, corg=0.05)
    with pytest.raises(ParameterMissingError):
        calc_hydraulic_properties(ld)


@pytest.mark.skip(
    reason="no way of currently testing this, wcmin corrected atm (check with David)"
)
def test_raise_for_bad_wcmin_wcmax():
    ld = LayerData(sand=0.1, clay=0.3, corg=1.0, bd=1.2)
    with pytest.raises(ValueError):
        calc_hydraulic_properties(ld)
