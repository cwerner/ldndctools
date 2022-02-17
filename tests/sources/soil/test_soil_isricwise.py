import numpy as np
import pytest

from ldndctools.sources.soil.soil_iscricwise import count_layers


def test_count_layers():
    assert count_layers([1, 2, 3, 4, -1, -1]) == 4
    assert count_layers([-1, 1, 2, 3, 4, 5]) == 0
    assert count_layers([-1, 1, 2, -1]) == 0


@pytest.mark.usefixtures("fake_isricwise")
class TestIsricWiseSoilDataset:
    def test_correct_count_of_masked_cells(self, fake_isricwise):
        assert np.count_nonzero(np.isnan(fake_isricwise.mask)) == 2
        assert np.count_nonzero(np.isnan(fake_isricwise.layer_mask)) == 2

    def test_mask_shapes(self, fake_isricwise):
        assert fake_isricwise.mask.shape == (3, 3)
        assert fake_isricwise.layer_mask.shape == (3, 3)

    def test_mask_values(self, fake_isricwise):
        a = np.unique(fake_isricwise.mask.values)
        b = np.array([1, np.nan])
        assert np.allclose(a, b, equal_nan=True)

        a = np.unique(fake_isricwise.layer_mask.values)
        b = np.array([1, 2, 3, np.nan])
        assert np.allclose(a, b, equal_nan=True)

    def test_attribute_conversion(self, fake_isricwise):
        assert set(fake_isricwise.data.data_vars) == {"bd", "ph", "clay"}
