from typing import Any, Optional, Union

import logging
import numpy as np
import rioxarray  # noqa
import xarray as xr

from ldndctools.misc.geohash import coords2geohash_dec
from ldndctools.cli.selector import CoordinateSelection, Selector
from ldndctools.io.xmlwriter import SiteXmlWriter
from ldndctools.misc.types import RES
from ldndctools.sources.soil.soil_base import SoilDataset

log = logging.getLogger(__name__)

log.setLevel("DEBUG")

def create_dataset(
    soil: SoilDataset,
    selector: Union[Selector, CoordinateSelection],
    res: RES,
    args,
    progressbar: Optional[Any] = None,
    status_widget: Optional[Any] = None,
):
    # soil = soil.load()
    # soil = soil.rio.write_crs(4326)

    if isinstance(selector, Selector):
        log.info("Using Selector")
        if selector.gdf_mask is None:
            log.info("No valid data to process for this region/ bbox request.")
            exit(1)

        # clip region selection
        soil.clip_mask_box(
            minx=selector._bbox.x1,
            miny=selector._bbox.y1,
            maxx=selector._bbox.x2,
            maxy=selector._bbox.y2,
        )
        soil.clip_mask(selector.gdf_mask.geometry, all_touched=True)

        xmlwriter = SiteXmlWriter(soil, res=res)
        if ('lat' in args) and ('lon' in args):
            sel = soil._soil.sel(lat=args.lat, lon=args.lon, method='nearest')
            cid = coords2geohash_dec( lat=sel["lat"].values.item(), lon=sel["lon"].values.item())
            site_xml = xmlwriter.write(progressbar=progressbar, status_widget=status_widget, id_selection=[cid])
        else:
            site_xml = xmlwriter.write(progressbar=progressbar, status_widget=status_widget)

    else:
        # WARNING: THIS BRANCH IS DEFUNCT!!!
        soil.clip_mask_box(
            minx=min(selector.lons),
            miny=min(selector.lats),
            maxx=max(selector.lons),
            maxy=max(selector.lats),
        )

        results = []
        for lat, lon in zip(selector.lats, selector.lons):
            results.append(soil.data.sel(lat=lat, lon=lon, method="nearest"))

        soil_new = xr.ones_like(soil.data) * np.nan
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
