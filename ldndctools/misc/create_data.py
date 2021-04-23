from typing import Union

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
    else:
        soil = soil.sel(lat=selector.lats, lon=selector.lons, method="nearest")

    xmlwriter = SiteXmlWriter(soil, res=res)
    site_xml = xmlwriter.write(progressbar=progressbar, status_widget=status_widget)
    site_nc = xmlwriter.arrays

    return site_xml, site_nc
