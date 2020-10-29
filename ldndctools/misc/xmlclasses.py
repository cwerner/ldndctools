import math
import xml.etree.cElementTree as et
import xml.dom.minidom as md

from ldndctools.misc.types import LayerData, NODATA


def calc_hydraulic_properties(ld: LayerData) -> LayerData:
    """Calc hydraulic properties based on et al. (1996)

    shape parameters: Woesten et al. (1999) Geoderma

    OM (% organic matter)
    D (bulk density)
    topsoil 1, subsoil 0
    C, S, (clay, silt in %)

    formula:
    θ_s = 0.7919 + 0.001691 * C - 0.29619 * D - 0.000001491 * S*S + \
          0.0000821 * OM * OM + 0.02427 * C**-1 + 0.01113 * S**-1 + \
          0.01472 * math.ln( S ) - 0.0000733 * OM * C - 0.000619 * D * C - \
          0.001183 * D * OM - 0.0001664 * topsoil * S

    ad-hoc AG Boden

    Sand, Clay [%], BD [g cm-3], Corg [%]
    """

    # convert units
    corg = ld.corg * 100
    clay = ld.clay * 100
    sand = ld.sand * 100
    bd = ld.bd

    theta_r = 0.015 + 0.005 * clay + 0.014 * corg
    theta_s = 0.81 - 0.283 * bd + 0.001 * clay

    log_n = 0.053 - 0.009 * sand - 0.013 * clay + 0.00015 * sand ** 2
    log_alpha = -2.486 + 0.025 * sand - 0.351 * corg - 2.617 * bd - 0.023 * clay

    alpha = math.e ** log_alpha
    vgn = math.e ** log_n
    vgm = 1.0  # (1.0 - (1.0/ vGn)) disabled as we do not use texture classes but real fractions

    field_capacity = theta_r + (theta_s - theta_r) / math.pow(
        (1.0 + math.pow(alpha * 100.0, vgn)), vgm
    )
    wilting_point = theta_r + (theta_s - theta_r) / math.pow(
        (1.0 + math.pow(alpha * 15800.0, vgn)), vgm
    )

    ld.wcmax = field_capacity * 1000
    ld.wcmin = wilting_point * 1000

    return ld


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
            lheight="0.0",
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

        ld.split = 1
        soil_layer = et.Element("layer", **ld.as_dict(ignore=["topd", "botd"]))

        if extra_split:
            # create identical top layer with finer discretization
            # TODO: write test to check expected stratification
            soil_layer_extra = soil_layer.copy()
            soil_layer_extra.attrib["depth"] = "20"
            soil_layer_extra.attrib["split"] = "4"

            self.xml.find("./soil/layers").append(soil_layer_extra)

            # adjust height of original layer to be consistent
            soil_layer.attrib["depth"] = "180"
            soil_layer.attrib["split"] = "9"

        self.xml.find("./soil/layers").append(soil_layer)
