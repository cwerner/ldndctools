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
        soil = soil.rio.clip_box(
            minx=min(selector.lons),
            miny=min(selector.lats),
            maxx=max(selector.lons),
            maxy=max(selector.lats),
        )

        results = []
        for lat, lon in zip(selector.lats, selector.lons):
            results.append(soil.sel(lat=lat, lon=lon, method="nearest"))

        soil_new = xr.ones_like(soil) * np.nan
        for p in results:
            for v in soil.data_vars:
                soil_new[v].loc[dict(lat=p.lat, lon=p.lon)] = p[v]

        xmlwriter = SiteXmlWriter(soil_new, res=res)
        site_xml = xmlwriter.write(
            progressbar=progressbar,
            status_widget=status_widget,
            coords=zip(selector.lons, selector.lats),
        )

    site_nc = xmlwriter.arrays

    return site_xml, site_nc
