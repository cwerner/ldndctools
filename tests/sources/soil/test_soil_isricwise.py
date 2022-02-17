import numpy as np
import pytest

from ldndctools.sources.soil.soil_iscricwise import count_layers


def test_count_layers():
    assert count_layers([1, 2, 3, 4, -1, -1]) == 4
    assert count_layers([-1, 1, 2, 3, 4, 5]) == 0
    assert count_layers([-1, 1, 2, -1]) == 0


@pytest.mark.usefixtures("isricwise_ds")
class TestIsricWiseSoilDataset:
    def test_correct_count_of_masked_cells(self, isricwise_ds):
        assert np.count_nonzero(np.isnan(isricwise_ds.mask)) == 48
        assert np.count_nonzero(np.isnan(isricwise_ds.layer_mask)) == 48

    def test_mask_shapes(self, isricwise_ds):
        assert isricwise_ds.mask.shape == (16, 22)
        assert isricwise_ds.layer_mask.shape == (16, 22)

    def test_mask_values(self, isricwise_ds):
        a = np.unique(isricwise_ds.mask.values)
        b = np.array([1, np.nan])
        assert np.allclose(a, b, equal_nan=True)

        a = np.unique(isricwise_ds.layer_mask.values)
        b = np.array([2, 5, np.nan])
        assert np.allclose(a, b, equal_nan=True)

    def test_attribute_conversion(self, isricwise_ds):
        assert set(isricwise_ds.data.data_vars) == {
            "bd",
            "depth",
            "corg",
            "norg",
            "sand",
            "silt",
            "clay",
            "scel",
            "ph",
        }
