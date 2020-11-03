import xarray as xr


class SiteNetcdfWriter:
    def __init__(self, mask, ids):
        mask.name = "mask"
        self.mask = mask
        self.ids = ids

    def write(self):
        ds = xr.Dataset()
        ds["selmask"] = self.mask
        ds["ids"] = self.ids
        return ds
