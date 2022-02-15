import xml.dom.minidom as md
import xml.etree.cElementTree as et

from ldndctools.misc.calculations import calc_hydraulic_properties
from ldndctools.misc.types import LayerData, NODATA


class BaseXML(object):
    def __init__(self, start_year: int = 2000, end_year: int = 2012, **kwargs):
        self.xml = None  # ET.Element("setups"), define by child
        self.startY = start_year
        self.endY = end_year
        self.tags = {}
        desc = et.Element("description")

        for t in "AUTHOR,EMAIL,DATE,DATASET,VERSION,SOURCE".split(","):
            if t in kwargs:
                e = et.SubElement(desc, t.lower())
                e.text = str(kwargs[t])
        self.tags["desc"] = desc

    def write(self, filename="all.xml"):
        out = md.parseString(et.tostring(self.xml)).toprettyxml()
        # fix special characters
        sc = {"&gt;": ">", "&lt;": "<"}
        for key, val in sc.items():
            out = out.replace(key, val)
        open(filename, "w").write(out)


class SiteXML(BaseXML):
    def __init__(self, **k):
        BaseXML.__init__(self, **k)

        _lat = str(k["lat"])
        _lon = str(k["lon"])
        _id = f'{k["id"]}' if "id" in k else "0"
        _use_history = str(k["usehistory"]) if "usehistory" in k else "arable"

        self.xml = et.Element("site", id=_id, lat=_lat, lon=_lon)
        self.xml.append(self.tags["desc"])

        kwargs = dict(
            usehistory=_use_history,
            soil="NONE",
            humus="NONE",
            litterheight="0.0",
            corg5=str(NODATA),
            corg30=str(NODATA),
        )

        et.SubElement(self.xml, "general")
        soil = et.SubElement(self.xml, "soil")
        et.SubElement(soil, "general", **kwargs)
        et.SubElement(soil, "layers")

    def add_soil_layer(
        self, ld: LayerData, litter: bool = False, extra_split: bool = False
    ):
        """ this adds a soil layer to the given site (to current if no ID given)"""
        # only calculate hydrological properties if we have a mineral soil layer added
        if not litter:
            ld = calc_hydraulic_properties(ld)

        if extra_split:
            # create identical top layer with finer discretization
            if ld.depth >= 40:
                ld_extra = ld.copy()
                ld_extra.depth = 20

                # adjust height of original top layer to be consistent
                ld.depth = ld.depth - 20

            soil_layer_extra = et.Element("layer", **ld_extra.serialize())
            self.xml.find("./soil/layers").append(soil_layer_extra)

        soil_layer = et.Element("layer", **ld.serialize())
        self.xml.find("./soil/layers").append(soil_layer)
