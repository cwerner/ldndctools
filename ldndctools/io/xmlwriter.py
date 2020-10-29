import numpy as np
import xarray as xr

from typing import Iterable, Optional, Tuple, Any

from ldndctools.misc.types import nmap
from ldndctools.misc.helper import mutually_exclusive
from ldndctools.misc.types import RES

import xml.dom.minidom as md
import xml.etree.cElementTree as et

from ldndctools.misc.xmlclasses import SiteXML
from ldndctools.misc.types import LayerData


def translate_data_format(d: xr.Dataset) -> Iterable[LayerData]:
    """ translate data from nc soil file (point-wise xarray selection) to new naming and units """

    data = []
    ks = nmap.keys()
    for lev in d.lev:
        ld = LayerData()

        for k in ks:
            name, conv, _ = nmap[k]
            setattr(ld, name, d.sel(lev=lev)[k].values.item() * conv)
        data.append(ld)
    return data


class SiteXmlWriter:
    """Site Xml File Writer"""

    def __init__(self, soil: xr.Dataset, res: RES):
        self.soil = soil
        self.mask = xr.where(soil.PROP1.sel(lev=1) > 0, 1, 0)
        self.mask = self.mask.where(self.mask == 1, self.mask)
        self.res = res
        self.ids = None

    @property
    def number_of_sites(self) -> int:
        return int(self.soil.PROP1.sel(lev=1).count().item())

    @property
    def arrays(self) -> xr.Dataset:
        ds = xr.Dataset()
        ds["mask"] = self.mask
        if self.ids is not None:
            ds["ids"] = self.ids
        return ds

    @mutually_exclusive("sample", "ids", "id_array", "coords")
    def write(
        self,
        sample: int = None,
        progressbar: Optional[Any] = None,
        status_widget: Optional[Any] = None,
        ids: Optional[Iterable[int]] = None,
        id_array: Optional[xr.DataArray] = None,
        coords: Optional[Iterable[Tuple[float, float]]] = None,
        extra_split: Optional[bool] = False,
    ) -> str:

        if status_widget:
            status_widget.warning("Preparing data")

        # use id mode 1000/ 10000 depending on resolution
        id_mode = 10000 if self.res in [RES.HR, RES.MR] else 1000
        ids = xr.zeros_like(self.mask)

        Lcids, Lix, Ljx, Dcids = [], [], [], {}

        for j in range(len(self.soil.lat)):
            for i in range(len(self.soil.lon)):
                if id_array:
                    cid = id_array.isel(lat=j, lon=i)
                else:
                    cid = (
                        ((len(self.soil.lat) - 1) - j) * id_mode + i
                        if self.soil.lat[0] < self.soil.lat[-1]
                        else j * id_mode + i
                    )
                ids[j, i] = cid
                Lcids.append(cid)
                Lix.append(i)
                Ljx.append(j)
                Dcids[(self.soil.lat.values[j], self.soil.lon.values[i])] = cid

        self.ids = xr.ones_like(self.mask) * np.nan
        self.ids[:] = ids
        self.ids = self.ids * self.mask

        def create_chunks(l):
            block = 200
            return [l[i : i + block] for i in range(0, len(l), block)]

        Lcids2d = create_chunks(Lcids)
        Lix2d = create_chunks(Lix)
        Ljx2d = create_chunks(Ljx)

        sites = []
        sb_cnt = 1
        cnt = 0

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

                # take point selection and return dict with modified data naming and units
                data = translate_data_format(d)

                # check for valid layer(s)
                if data[0].topd >= 0.0 and (data[0].botd - data[0].topd) * 10 > 0:
                    site = SiteXML(
                        lat=lat, lon=lon, id=Dcids[(lat, lon)]
                    )  # **BASEINFO)

                    # 5 layers !!!
                    for i in range(5):
                        lay = data[i]

                        if lay.topd >= 0.0:
                            lay.depth = (lay.botd - lay.topd) * 10
                        if i in [0, 1]:
                            lay.split = 10
                        elif i in [2, 3]:
                            lay.split = 4
                        else:
                            lay.split = 2

                        # default iron percentage
                        lay.iron = 0.01

                        if i == 0 and extra_split:
                            site.add_soil_layer(
                                lay, litter=False, extra_split=extra_split
                            )
                        else:
                            site.add_soil_layer(lay, litter=False)
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
