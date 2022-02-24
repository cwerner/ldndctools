from abc import ABCMeta

import pytest
import xarray as xr

from ldndctools.sources.soil.soil_base import SoilDataset


class TestSoilDataset:
    def test_isabstractbaseclass(self):
        assert isinstance(SoilDataset, ABCMeta)

    def test_subclass_requires_attributes_raise_if_missing(self):
        with pytest.raises(NotImplementedError):

            class DummySoilDataset(SoilDataset):
                pass

        with pytest.raises(NotImplementedError):

            class AnotherDummySoilDataset(SoilDataset):
                _wrong_name = "nothing"

    def test_abstractmethods_exist(self):
        SoilDataset.__abstractmethods__ = set()

        class DummySoilDataset(SoilDataset):
            _source_attrs = []
            _mapper = []

        d = DummySoilDataset()

        mask = d._build_mask(xr.Dataset())
        converter = d._converter()
        assert mask is None
        assert converter is None

    def test_property_masks(self):
        class DummySoilDataset(SoilDataset):
            _source_attrs = []
            _mapper = []

        d = DummySoilDataset()
        d._mask = xr.DataArray()
        assert d.mask is not None
        assert d.layer_mask is not None

    def test_property_original(self):
        class DummySoilDataset(SoilDataset):
            _source_attrs = []
            _mapper = []

        d = DummySoilDataset()
        d._soil = xr.DataArray()
        assert d.original is not None

    def test_property_data(self):
        class DummySoilDataset(SoilDataset):
            _source_attrs = []
            _mapper = []

        d = DummySoilDataset()
        d._soil = None
        assert d.data is None

        d._soil = xr.Dataset()
        assert isinstance(d.data, xr.Dataset)
