import xml.etree.cElementTree as ET
import xml.dom.minidom as MD

from ldndctools.misc.functions import calcHydaulicProperties

NODATA = "-99.99"


class BaseXML(object):
    def __init__(self, startY=2000, endY=2012, **kwargs):
        self.xml = None  # ET.Element("setups"), define by child
        self.startY = startY
        self.endY = endY
        self.tags = {}
        # --- dict of initial xml tags
        desc = ET.Element("description")

        for t in "AUTHOR,EMAIL,DATE,DATASET,VERSION,SOURCE".split(","):
            if t in kwargs:
                e = ET.SubElement(desc, t.lower())
                e.text = t
        self.tags["desc"] = desc

    def write(self, ID=None, filename="all.xml"):
        strOut = MD.parseString(ET.tostring(self.xml)).toprettyxml()
        # fix special characters
        sc = {"&gt;": ">", "&lt;": "<"}
        for key, val in sc.items():
            strOut = string.replace(strOut, key, val)
        open(filename, "w").write(strOut)


class SiteXML(BaseXML):
    def __init__(self, **k):
        BaseXML.__init__(self, **k)

        lat, lon = str(k["lat"]), str(k["lon"])

        theId = "%d" % k["id"] if "id" in k else "0"
        theUsehistory = str(k["usehistory"]) if "usehistory" in k else "arable"

        self.xml = ET.Element("site", id=theId, lat=lat, lon=lon)
        self.xml.append(self.tags["desc"])

        # gernal tags
        general = ET.SubElement(self.xml, "general")

        # soil tags
        soil = ET.SubElement(self.xml, "soil")

        dargs = dict(
            usehistory=theUsehistory,
            soil="NONE",
            humus="NONE",
            lheight="0.0",
            corg5=NODATA,
            corg30=NODATA,
        )
        ET.SubElement(soil, "general", **dargs)
        layers = ET.SubElement(soil, "layers")

    def addSoilLayer(self, DATA, ID=None, litter=False, accuracy={}, extra_split=False):
        """ this adds a soil layer to the given site (to current if no ID given)"""
        # only calculate hydr. properties if we have a mineral soil layer added
        if litter == False:
            DATA["wcmax"], DATA["wcmin"] = calcHydaulicProperties(DATA)

        dargs = {
            k: NODATA
            for k in "depth,split,ph,scel,bd,sks,norg,corg,clay,wcmax,wcmin,sand,silt,iron".split(
                ","
            )
        }
        dargs["split"] = "1"
        soilLayer = ET.Element("layer", **dargs)
        keys = DATA.keys()
        for k in keys:
            digits = 2
            if k in accuracy.keys():
                digits = accuracy[k]
                if digits == 0:
                    # int
                    soilLayer.attrib[k] = str(int(round(DATA[k], digits)))
                else:
                    soilLayer.attrib[k] = str(round(DATA[k], digits))

        if extra_split:
            # create identical top layer with finer discretization
            soilLayerExtra = soilLayer.copy()
            soilLayerExtra.attrib["depth"] = 20
            soilLayerExtra.attrib["split"] = 4

            self.xml.find("./soil/layers").append(soilLayerExtra)

            # adjust height of original layer to be consistent
            soilLayer.attrib["depth"] = 180
            soilLayer.attrib["split"] = 9

        self.xml.find("./soil/layers").append(soilLayer)
