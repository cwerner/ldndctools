import xarray as xr
import rioxarray

from ldndctools.cli.selector import Selector
from ldndctools.misc.types import RES
from ldndctools.io.xmlwriter import SiteXmlWriter


def create_dataset(
    soil: xr.Dataset, selector: Selector, res: RES, progressbar, status_widget=None
):
    soil = soil.load()
    soil = soil.rio.write_crs("epsg:4326")
    soil = soil.rio.clip(selector.gdf_mask.geometry, selector.gdf_mask.crs)
    soil = soil.where(soil.PROP1.sel(lev=1) > 0)

    xmlwriter = SiteXmlWriter(soil, res=res)
    site_xml = xmlwriter.write(progressbar=progressbar, status_widget=status_widget)
    site_nc = xmlwriter.arrays

    return site_xml, site_nc
