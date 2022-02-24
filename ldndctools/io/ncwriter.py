import xarray as xr


class SiteNetcdfWriter:
    def __init__(self, mask, ids):
        mask.name = "soilmask"
        self.mask = mask
        self.ids = ids

    def write(self):
        ds = xr.Dataset()
        ds["soilmask"] = self.mask
        ds["ids"] = self.ids
        return ds
