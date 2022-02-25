import xml.dom.minidom as md
import xml.etree.cElementTree as et
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import xarray as xr
from pydantic import ValidationError

from ldndctools.misc.geohash import coords2geohash_dec
from ldndctools.misc.helper import mutually_exclusive
from ldndctools.misc.types import LayerData, RES
from ldndctools.misc.xmlclasses import SiteXML
from ldndctools.sources.soil.soil_base import SoilDataset


def translate_data_format(d: xr.Dataset) -> List[LayerData]:
    """translate data from nc soil file (point-wise xarray sel) to new naming/ units"""

    data: List[LayerData] = []
    for lev in d.lev:
        ld = LayerData()

        # TODO: catch this more elegantly via mask/ layer_mask
        if np.isnan(d.sel(lev=lev)["depth"]):
            continue

        for varname, value in d.data_vars.items():
            data = value.sel(lev=lev).values.item()  # type: ignore
            try:
                setattr(ld, varname, data)
            except ValidationError:
                setattr(ld, varname, None)
        data.append(ld)
    return data


class SiteXmlWriter:
    """Site Xml File Writer"""

    def __init__(self, soil: SoilDataset, res: RES):
        self.soil = soil.data
        self.mask = soil.mask
        self.ids: Optional[xr.DataArray] = None
        self.res = res

    @property
    def number_of_sites(self) -> int:
        assert self.mask is not None
        return self.mask.sum().item()

    @property
    def arrays(self) -> xr.Dataset:
        ds = xr.Dataset()
        ds["soilmask"] = self.mask
        if self.ids is not None:
            ds["siteid"] = self.ids
        return ds

    @mutually_exclusive("sample", "ids", "id_array", "coords")
    def write(
        self,
        sample: Optional[int] = None,
        progressbar: Optional[Any] = None,
        status_widget: Optional[Any] = None,
        ids: Optional[Iterable[int]] = None,
        id_array: Optional[xr.DataArray] = None,
        coords: Optional[Iterable[Tuple[float, float]]] = None,
        extra_split: Optional[bool] = True,
    ) -> str:

        if status_widget:
            status_widget.warning("Preparing data")

        ids: xr.DataArray = xr.zeros_like(self.mask, dtype=np.int32)

        Lcids: List[int] = []
        Lix: List[int] = []
        Ljx: List[int] = []
        Dcids: Dict[Tuple[float, float], int] = {}

        for j in range(len(self.soil.coords["lat"])):
            for i in range(len(self.soil.coords["lon"])):
                if id_array:
                    cid: int = id_array.isel(lat=j, lon=i)
                else:
                    cid: int = coords2geohash_dec(
                        lat=self.soil.coords["lat"][j].values.item(),
                        lon=self.soil.coords["lon"][i].values.item(),
                    )
                # print(cid)
                ids[j, i] = cid
                Lcids.append(cid)
                Lix.append(i)
                Ljx.append(j)
                Dcids[
                    (
                        self.soil.coords["lat"].values[j],
                        self.soil.coords["lon"].values[i],
                    )
                ] = cid

        self.ids = ids * self.mask

        def create_chunks(items: List[int]) -> List[List[int]]:
            block = 200
            return [items[item : item + block] for item in range(0, len(items), block)]

        Lcids2d = create_chunks(Lcids)
        Lix2d = create_chunks(Lix)
        Ljx2d = create_chunks(Ljx)

        sites = []

        # NOTE: Possibly some selection missing
        step = 0
        total_steps = self.number_of_sites

        for Lix, Ljx, Lcids in zip(Lix2d, Ljx2d, Lcids2d):

            subset = self.soil.isel(
                lat=xr.DataArray(np.array(Ljx), dims="points"),
                lon=xr.DataArray(np.array(Lix), dims="points"),
            )

            for point in subset.points:
                d = subset.sel(points=point)
                lat, lon = float(d.lat), float(d.lon)

                # take point sel and return dict with modified data naming/ units
                # TODO: do proper mask checking
                if not np.isnan(d.sel(lev=1)["depth"].values.item()):
                    data = translate_data_format(d)

                    site = SiteXML(
                        lat=lat, lon=lon, id=Dcids[(lat, lon)]
                    )  # **BASEINFO)

                    add_site = False
                    for i, lay in enumerate(data):
                        assert i < 5, "Currently max of 5 layers expected"

                        # abort if we have no valid data for layer
                        if None in [lay.ph, lay.bd, lay.clay, lay.sand]:
                            break

                        # default iron percentage
                        lay.iron = 0.01

                        if i == 0 and extra_split:
                            site.add_soil_layer(
                                lay, litter=False, extra_split=extra_split
                            )
                        else:
                            site.add_soil_layer(lay, litter=False)
                        add_site = True

                    if add_site:
                        sites.append(site)

                    if progressbar:
                        if hasattr(progressbar, "progress"):
                            progressbar.progress(step / total_steps)
                        else:
                            progressbar.update(1 / total_steps)
                        step += 1

                    if status_widget:
                        status_widget.warning(f"{(step/total_steps)*100:.1f}% done")

        # create xml
        xml = et.Element("ldndcsite")
        for site_cnt, site in enumerate(sites):
            x = site.xml.find("description")
            if site_cnt == 0:
                xml.append(x)
            site.xml.remove(x)
            xml.append(site.xml)
        return md.parseString(et.tostring(xml)).toprettyxml()
