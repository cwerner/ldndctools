from typing import Union

import numpy as np
import rioxarray  # noqa
import xarray as xr

from ldndctools.cli.selector import CoordinateSelection, Selector
from ldndctools.io.xmlwriter import SiteXmlWriter
from ldndctools.misc.types import RES


def create_dataset(
    soil: xr.Dataset,
    selector: Union[Selector, CoordinateSelection],
    res: RES,
    progressbar,
    status_widget=None,
):
    soil = soil.load()
    soil = soil.rio.write_crs(4326)

    if isinstance(selector, Selector):
        soil = soil.rio.clip(selector.gdf_mask.geometry)
        soil = soil.where(soil.PROP1.sel(lev=1) > 0)
        xmlwriter = SiteXmlWriter(soil, res=res)
        site_xml = xmlwriter.write(progressbar=progressbar, status_widget=status_widget)

    else:
        # TODO: this should be possible to achieve in a cleaner way!
        soil_orig = soil.sel(lat=selector.lats, lon=selector.lons, method="nearest")
        selected_lats = xr.DataArray(selector.lats, dims="points")
        selected_lons = xr.DataArray(selector.lons, dims="points")
        soil_pointwise = soil_orig.sel(
            lat=selected_lats, lon=selected_lons, method="nearest"
        )

        soil_new = xr.ones_like(soil_orig) * np.nan
        for p in soil_pointwise.points:
            s = soil_pointwise.sel(points=p)
            for v in soil_pointwise.data_vars:
                soil_new[v].loc[dict(lat=s.lat, lon=s.lon)] = s[v]

        xmlwriter = SiteXmlWriter(soil_new, res=res)
        site_xml = xmlwriter.write(
            progressbar=progressbar,
            status_widget=status_widget,
            coords=zip(selector.lons, selector.lats),
        )

    site_nc = xmlwriter.arrays

    return site_xml, site_nc
