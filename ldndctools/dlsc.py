#!/usr/bin/env python3
# Dynamic LandscapeDNDC Sitefile Creator (DLSC v0.1)
#
# Use this tool to build XML LDNDC site files
# __________________________________________________
# 2019/10/13, christian.werner@kit.edu
#
# descr: dynamically select regions and create (arable) LDNDC
#        site.xml file
#
#
# Christian Werner (IMK-IFU, KIT)
# christian.werner@kit.edu

import xarray as xr
import numpy as np
import pandas as pd
import os, datetime, shutil, string, math, progressbar
from optparse import OptionParser
import xml.dom.minidom as MD
import xml.etree.cElementTree as ET

# ---------------------------------------------------------------------
#  Default info for this dataset
# ---------------------------------------------------------------------
AUTHOR = "Christian Werner"
EMAIL = "christian.werner@kit.edu"
DATE = str(datetime.datetime.now())
DATASET = "created using [D]ynamic [L]andscapeDNDC [S]itefile [C]reator (v0.1)"
VERSION = "v0.1"
SOURCE = "IMK-IFU, KIT"

NODATA = "-99.99"

# XML code / sourced from Vietnam project:
# preprocessor_v1.py and create_ldndc_site_setup_base.py


class BaseXML(object):
    def __init__(self, startY=2000, endY=2012):
        self.xml = None  # ET.Element("setups"), define by child
        self.startY = startY
        self.endY = endY
        self.tags = {}
        # --- dict of initial xml tags
        desc = ET.Element("description")
        e = ET.SubElement(desc, "author")
        e.text = AUTHOR
        e = ET.SubElement(desc, "email")
        e.text = EMAIL
        e = ET.SubElement(desc, "date")
        e.text = DATE
        e = ET.SubElement(desc, "dataset")
        e.text = DATASET
        e = ET.SubElement(desc, "version")
        e.text = VERSION
        e = ET.SubElement(desc, "source")
        e.text = SOURCE
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
        BaseXML.__init__(self)

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


# ------------------------------------------- F U N C T I O N S --------------------------------------------
def calcLitter(litterMass, litname):  # mass in t C ha-1
    if litname == "MULL":
        density = 0.2
        accumulationFactor = 1.5
    elif litname == "MODER":
        density = 0.25
        accumulationFactor = 2.5
    else:
        density = 0.3
        accumulationFactor = 3.5

    # explanation:
    #   (tCha-1) > x2 > tBMha-1 > x0.1 > kgBMm-2 > x0.1 > gBMcm-2 > /density > height_cm > *10 > height_mm
    # littermass (t C ha-1) * 2 (BM conv) * 0.1 * 0.1 / density * 10
    depth = ((litterMass * accumulationFactor * 2 * 0.1 * 0.1) / density) * 10.0
    numberOfLayers = math.floor(depth / 20.0)
    layerHeight = depth
    if numberOfLayers != 0:
        layerHeight = 20.0 + ((depth % 20.0) / numberOfLayers)
    return (density, depth, layerHeight)


def calcHeight(TK, N):
    if TK == -9999:
        TKmm = -9999
    else:
        TKmm = TK * 10  # change the unit from cm to mm

    if TKmm > -9999:
        numberOfLayers = math.floor(TKmm / N)
        if numberOfLayers != 0:
            layerHeight = N + ((TKmm % N) / numberOfLayers)
        else:
            layerHeight = TKmm
    else:
        layerHeight = -9999
    return (TKmm, layerHeight)


def calcHydaulicProperties(D):
    """ Calc hydraulic properties based on et al. (1996) """
    # shape parameters Woesten et al. (1999) Geoderma
    #
    # OM      (% organic matter)
    # D       (bulk denisty)
    # topsoil 1, subsoil 0
    # C, S,   (clay, silt in %)
    #
    # ThetaS = 0.7919 + 0.001691 * C - 0.29619 * D - 0.000001491 * S*S + 0.0000821 * OM * OM + 0.02427 * C**-1 + 0.01113 * S**-1 + \
    #         0.01472 * math.ln( S ) - 0.0000733 * OM * C - 0.000619 * D * C - 0.001183 * D * OM - 0.0001664 * topsoil * S

    # ad-hoc AG Boden
    #
    # Sand, Clay [%], BD [g cm-3], corg [%]

    corg = D["corg"] * 100
    clay = D["clay"] * 100
    sand = D["sand"] * 100
    bd = float(D["bd"])

    ThetaR = 0.015 + 0.005 * clay + 0.014 * corg
    ThetaS = 0.81 - 0.283 * bd + 0.001 * clay

    logAlpha = -2.486 + 0.025 * sand - 0.351 * corg - 2.617 * bd - 0.023 * clay
    logN = 0.053 - 0.009 * sand - 0.013 * clay + 0.00015 * sand ** 2

    try:
        ALPHA = math.e ** logAlpha
    except:
        print(D)
    vGn = math.e ** logN
    vGm = 1.0  # (1.0 - (1.0/ vGn)) disabled as we do not use texture classes but real fractions

    FLDcap = ThetaR + (ThetaS - ThetaR) / math.pow(
        (1.0 + math.pow(ALPHA * 100.0, vGn)), vGm
    )
    WILTpt = ThetaR + (ThetaS - ThetaR) / math.pow(
        (1.0 + math.pow(ALPHA * 15800.0, vGn)), vGm
    )
    return FLDcap * 1000, WILTpt * 1000


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = MD.parseString(rough_string)
    str1 = reparsed.toprettyxml(indent="  ")
    str2 = []
    ss = str1.split("\n")
    for s in ss:
        x = "".join(s.split())
        if x != "":
            str2.append(s)
    return "\n".join(str2) + "\n"


def translateDataFormat(d):
    """ translate data from nc soil file (pointwise xarray sel) to new naming and units """
    data = []
    size = len(d.lev)  # number of layers (5)

    ks = nmap.keys()
    for l in range(size):
        od = {}
        for k in ks:
            name, conv, ignore = nmap[k]
            od[name] = float(d.sel(lev=l + 1)[k]) * conv
        data.append(od)
    return data


# soil
nmap = {
    "TOTC": ("corg", 0.001, 5),
    "TOTN": ("norg", 0.001, 6),
    "PHAQ": ("ph", 1, 2),
    "BULK": ("bd", 1, 2),
    "CFRAG": ("scel", 0.01, 2),
    "SDTO": ("sand", 0.01, 2),
    "STPC": ("silt", 0.01, 2),
    "CLPC": ("clay", 0.01, 2),
    "TopDep": ("topd", 1, 0),
    "BotDep": ("botd", 1, 0),
}

cmap = dict((x[0], x[2]) for x in nmap.values())
cmap["depth"] = 0
cmap["split"] = 0
cmap["wcmin"] = 1
cmap["wcmax"] = 1
cmap["iron"] = 5


# --------------------------- END


def print_table(seq, columns=2, base=0):
    """ print input selection table """
    table = ""
    a = 0

    # expand to muliple
    fullSize = int(math.ceil(len(seq) / float(columns))) * columns
    labels = np.array(seq + [""] * (fullSize - len(seq)), dtype=object).reshape(
        -1, int(fullSize / columns)
    )
    labels = labels.T

    vals = []
    keys = []

    for i in range(len(labels[0])):
        for j in range(len(labels)):
            la = i * len(labels) + j + base
            if labels[j, i] != "":
                vals.append(labels[j, i])

                labels[j, i] = "[%d] " % la + labels[j, i]

                keys.append(la)

    t = []
    for row in labels:
        t.append("".join([x.ljust(35) for x in row]))

    print("\n".join(t) + "\n")


# -----------------------------------------------------------


class MyParser(OptionParser):
    def format_epilog(self, formatter):
        return self.epilog


if __name__ == "__main__":

    parser = MyParser(
        "usage: %prog [options] outfile",
        epilog="""

Example usage:
python DLSC_v0.1py -r HR sites_EU28.xml

Help:
-h, --help
""",
    )

    parser.add_option(
        "-b",
        "--bbox",
        dest="bbox",
        default=None,
        help="bbox for netCDF output [x1,y1,x2,y2]",
    )

    parser.add_option(
        "-f",
        "--file",
        dest="file",
        default=None,
        help="infile with lat lon coordinates",
    )

    parser.add_option(
        "-r",
        "--res",
        dest="resolution",
        default="HR",
        help="select resolution: HR (0.083deg), MR (0.25deg) or LR (0.5deg)",
    )

    parser.add_option(
        "--region",
        dest="rcode",
        default=None,
        help="for non-interactive execution provide region code(s) [chain with +]",
    )

    parser.add_option(
        "--country",
        dest="ccode",
        default=None,
        help="for non-interactive execution provide country code(s) [chain with +]",
    )

    parser.add_option(
        "--extra-split",
        action="store_true",
        dest="extrasplit",
        default=False,
        help="subdivide the first soil layer (rice sims)",
    )

    (options, args) = parser.parse_args()

    print(
        "____________________________________________________________________________"
    )
    print()
    print("        [D]ynamic [L]andscapeDNDC [S]itefile [C]reator (DLSC v0.1)")
    print()
    print("              ... use this tool to build XML LDNDC site files")
    print(
        "____________________________________________________________________________"
    )
    print("2019/10/13, christian.werner@kit.edu")
    print()

    # delete later
    DEBUG = True
    INTERACTIVE = True

    if (
        (options.rcode is not None)
        or (options.ccode is not None)
        or (options.file is not None)
    ):
        print("Non-interactive mode...")
        INTERACTIVE = False

    # query environment or command flags for selection (non-intractive mode)
    options.rcode = os.environ.get("DLSC_REGION", options.rcode)
    options.ccode = os.environ.get("DLSC_COUNTRY", options.ccode)

    # single country selection
    if (options.rcode is None) and (options.ccode is not None):
        options.rcode = "c"

    dres = dict(LR="0.5x0.5deg", MR="0.25x0.25deg", HR="0.0833x0.0833deg")

    if options.resolution in ["LR", "MR", "HR"]:
        SOIL = f"data/soil/GLOBAL_WISESOIL_S1_{options.resolution}.nc"
        ADMIN = f"data/tmworld/tmworld_{options.resolution}.nc"
        resStr = dres[options.resolution]
    else:
        print(f"Wrong resolution: {options.resolution}. Use HR, MR or LR.")
        exit(-1)

    if len(args) == 0:
        outname = "sites_%s.xml" % options.resolution
    else:
        outname = args[0]
        if ("LR" not in outname) and ("HR" not in outname) and ("MR" not in outname):
            if outname[-4:] == ".xml":
                outname = outname[:-4] + "_" + options.resolution + ".xml"
            else:
                outname = outname + "_" + options.resolution + ".xml"

    print("Soil resolution: %s [%s]" % (options.resolution, resStr))
    print("Outfile name:   ", outname)

    # get cell mask from soil/ admin intersect
    dss = xr.open_dataset(SOIL).sel(lev=1)["PROP1"]
    soilmask = np.ma.where(dss.to_masked_array() > 0, 1, 0)

    # countries
    df = pd.read_csv("data/tmworld/tmworld_full_lut.txt", sep="\t")

    # eu28 specific
    eu28 = "BE,DE,FR,IT,LU,NL,DK,IE,GB,GR,PT,ES,FI,AT,SE,EE,LV,LT,MT,PL,SK,SI,CZ,HU,CY,BG,RO,HR".split(
        ","
    )

    df_extra = df[df["ISO2"].isin(eu28)]
    Dextracountries = dict(zip(df_extra.NAME, df_extra.UN))

    # for menu, only pick bigger ones
    df = df[df.POP2005 > 1000000]
    Dcountries = dict(zip(df.NAME, df.UN))

    # regions
    dfr = pd.read_csv("data/tmworld/tmworld_regions_lut.txt", sep="\t")
    Dregions = dict(zip(dfr.R_Name, dfr.R_Code))

    # subregions
    dfsr = pd.read_csv("data/tmworld/tmworld_subregions_lut.txt", sep="\t")
    Dsubregions = dict(zip(dfsr.SR_Name, dfsr.SR_Code))

    # lists with selection ids for tmworld netcdfs
    UNR = []
    UNSR = []
    UNC = []

    # special flags (TODO: cleanup later)
    eu28 = False
    world = False

    if options.rcode:
        UNR.append(options.rcode)
    if options.ccode:
        UNC.append(options.ccode)

    if INTERACTIVE:

        print("\nPlease make your region/ country selection [use codes]")
        print('Multiple selections are allowed [i.e. "12+13+17"]\n')
        print('If you want to include a specific country type "c" in selection.')
        print('You can also add a country to a region [i.e. "27+c"]')
        print("\nRegions:")
        seq1 = sorted(Dregions.keys())
        print_table(seq1, 1)

        print("Sub-Regions:")
        seq2 = sorted(Dsubregions.keys())

        print_table(seq2, 3, base=len(seq1))

        # manually add some regions:

        print("Special:")
        seq_extra = ["EU28", "WORLD"]
        print_table(seq_extra, 1, base=len(seq1) + len(seq2))
        seq2.append("EU28")  # 2nd last
        seq2.append("WORLD")  # last

        # INPUT LOOP
        showCountries = False
        repeat = True
        valItems = []

        # (sub-)region selection section
        while repeat:
            # query if not set programatically
            if options.rcode in [None]:
                x = input("Select (sub-)region (multiple: +; c: add countries): ")
            else:
                x = options.rcode

            if x == "":
                showCountries = True
                break

            if "+" in x:
                items = x.split("+")
            else:
                items = [x]

            print(items)

            # validate items
            for it in items:
                if it.lower() == "c":
                    showCountries = True
                    repeat = False
                else:
                    try:
                        I = int(it)
                        if I in range(len(seq1) + len(seq2)):
                            repeat = False

                            # catch specific regions and pass to country selector
                            if I == range(len(seq1) + len(seq2))[-2]:
                                eu28 = True
                            elif I == range(len(seq1) + len(seq2))[-1]:
                                world = True
                            else:
                                valItems.append(I)
                        else:
                            print(
                                "Invalid Entry (0...%d) %d"
                                % (len(seq1) + len(seq2) - 1, I)
                            )

                    except ValueError:
                        print("Invalid Entry")

        # create human-readable selection lists
        selPrint1 = []
        selPrint2 = []
        for I in valItems:
            if I < len(seq1):
                reg = seq1[I]
                UNR.append(Dregions[reg])
                selPrint1.append(reg)
            else:
                reg = seq2[I - len(seq1)]
                UNSR.append(Dsubregions[reg])
                selPrint1.append(reg)

        # special case EU28
        if eu28:
            selPrint1.append("EU28")
        if world:
            selPrint1.append("WORLD")

        # country selection section
        if showCountries == True:
            print("\nCountries:")

            seq3 = sorted(Dcountries.keys())

            # shorten long print columns
            def shorten(x):
                maxL = 25
                if len(x) >= maxL:
                    x = x[: maxL - 3] + "..."
                return x

            seqPrint = [shorten(k) for k, v in Dcountries.items()]
            print_table(sorted(seqPrint), 3)

            repeat = True

            while repeat:
                # query if not set programatically
                if options.ccode is None:
                    x = input("Select country (multiple: +): ")
                else:
                    x = options.ccode

                if "+" in x:
                    items = x.split("+")
                else:
                    items = [x]

                # validate items
                valItems = []
                for it in items:
                    try:
                        I = int(it)
                        if I in range(len(seq3)):
                            repeat = False
                            valItems.append(I)
                            reg = seq3[I]
                            UNC.append(Dcountries[reg])
                            selPrint2.append(reg)

                        else:
                            print("Invalid Entry (0...%d) %d" % (len(seq3) - 1, I))

                    except ValueError:
                        print("Invalid Entry")

        # if eu28 was selected add those ids now
        if eu28 == True:
            UNC += Dextracountries.values()

        print("\n----------------------------------")
        print("SELECTION")
        if len(selPrint1) > 0:
            print("Region  : ", "; ".join(selPrint1))
        if len(selPrint2) > 0:
            print("Country : ", "; ".join(selPrint2))

    def createMask(nc, vals, mask=None):
        da = nc.values
        if mask is not None:
            mask = np.zeros_like(da)
        for i in vals:
            mask = np.where(da == i, 1, mask)

        return mask

    # file mode: create mask from coordinates
    def createMask_fromfile(ds, infile):
        df = pd.read_csv(infile, delim_whitespace=True)
        x = ds.sel(lat=list(df.lat), lon=list(df.lon), method="nearest")
        ds_x = xr.zeros_like(ds)
        for _, r in df.iterrows():
            ds_x.loc[dict(lon=r.lon, lat=r.lat, method="nearest")] = 1

        return ds_x.values

    # get lats, lons
    with xr.open_dataset(ADMIN) as ds:
        lats = ds["lat"].values
        lons = ds["lon"].values

        # init empty mask
        mask = np.zeros_like(ds.UN.values)

        # use coords from file
        if options.file:
            mask = createMask_fromfile(ds.UN, options.file)

        # populate mask (incrementally)
        if len(UNR) > 0:
            mask = createMask(ds.REGION, UNR, mask=mask)
        if len(UNSR) > 0:
            mask = createMask(ds.SUBREGION, UNSR, mask=mask)
        if len(UNC) > 0:
            mask = createMask(ds.UN, UNC, mask=mask)

        # if world was selected, use entire mask
        if world:
            mask = np.where(ds.UN.values > 0, 1, 0)

    print("\nNumber of sites/ cells:")
    print(" region mask:", int(np.sum(mask)))
    mask *= soilmask
    print(" + soil mask:", int(np.sum(mask)))
    print("----------------------------------\n")

    ids = np.zeros_like(mask)

    if world and options.resolution == "HR":
        print("\nWARNING  You selected the entire world in high-res as a domain.")
        print("         This will take a loooooooooong time.\n")
        x = raw_input("[p] to proceed, anything else to abort")

        if string.lower(x) == "p":
            pass
        else:
            exit(1)

    # MAIN LOOP
    # iterate over mask to build XML
    ds = xr.open_dataset(SOIL)

    Lcids = []
    Lix = []
    Ljx = []

    Dcids = {}

    # cid mode
    # if LR: 1000
    # if MR/HR: 10000

    if options.resolution in ["HR", "MR"]:
        M = 10000
    else:
        M = 1000

    LATS = ds.coords["lat"].values

    for j in range(len(mask)):
        for i in range(len(mask[0])):
            if mask[j, i] == 1:
                if LATS[0] < 0.0:
                    cid = ((len(mask) - 1) - j) * M + i
                else:
                    cid = j * M + i

                ids[j, i] = cid

                Lcids.append(cid)
                Lix.append(i)
                Ljx.append(j)
                # Dcids[(ds.coords['lat'].values[j], ds.coords['lon'].values[i])] = cid
                Dcids[(LATS[j], ds.coords["lon"].values[i])] = cid

    # print(list(Dcids.items())[0])

    # punch out soil id coordinate (by segment of 1000 cells max. each for speed reasons)
    COORDTHRESHOLD = 200

    Lcids2d = [
        Lcids[i : i + COORDTHRESHOLD] for i in range(0, len(Lcids), COORDTHRESHOLD)
    ]
    Lix2d = [Lix[i : i + COORDTHRESHOLD] for i in range(0, len(Lix), COORDTHRESHOLD)]
    Ljx2d = [Ljx[i : i + COORDTHRESHOLD] for i in range(0, len(Ljx), COORDTHRESHOLD)]

    sites = []
    sbCnt = 1

    cnt = 0

    bar = progressbar.ProgressBar(
        maxval=len(Lcids),
        term_width=80,
        widgets=[
            progressbar.Bar("=", " %s [" % "Status: extracting sites", "]"),
            " ",
            progressbar.SimpleProgress(),
            " ",
            progressbar.Percentage(),
        ],
    ).start()

    # regional subset first to savetime
    min_lat = ds["lat"].isel(lat=min(Ljx))
    max_lat = ds["lat"].isel(lat=max(Ljx))

    min_dlat = min(Ljx)
    min_dlon = min(Lix)

    min_lon = ds["lon"].isel(lon=min(Lix))
    max_lon = ds["lon"].isel(lon=max(Lix))

    ds_ = ds.sel(lat=slice(min_lat, max_lat), lon=slice(min_lon, max_lon))

    for Lix, Ljx, Lcids in zip(Lix2d, Ljx2d, Lcids2d):
        # print "processing site batch %d of %d" % (sbCnt, len(Lcids2d))
        dx = ds_.isel_points(lat=np.array(Ljx) - min_dlat, lon=np.array(Lix) - min_dlon)

        for dp in dx.points:
            d = dx.sel(points=dp)

            site = SiteXML(
                lat=float(d.lat),
                lon=float(d.lon),
                id=Dcids[(float(d.lat), float(d.lon))],
            )  # id=Lcids[int(dp)] )

            # take point selection and return dict with modified data naming and units
            data2 = translateDataFormat(d)

            addFlag = False
            if data2[0]["topd"] >= 0.0 and (
                (data2[0]["botd"] - data2[0]["topd"]) * 10 > 0
            ):
                addFlag = True

            # 5 layers !!!
            for l in range(5):
                if data2[l]["topd"] >= 0.0:
                    data2[l]["depth"] = (data2[l]["botd"] - data2[l]["topd"]) * 10
                    if l in [0, 1]:
                        split = 10
                    elif l in [2, 3]:
                        split = 4
                    else:
                        split = 2
                    data2[l]["split"] = split

                    # default iron percentage
                    data2[l]["iron"] = 0.01

                    data2[l].pop("topd")
                    data2[l].pop("botd")

                    if l == 0 and options.extrasplit:
                        site.addSoilLayer(
                            data2[l],
                            litter=False,
                            accuracy=cmap,
                            extra_split=options.extrasplit,
                        )
                    else:
                        site.addSoilLayer(data2[l], litter=False, accuracy=cmap)

            if addFlag == True:
                sites.append(site)

            bar.update(cnt)
            cnt += 1

        sbCnt += 1

    # end bar
    bar.finish()

    # write XML file
    # merge site chunks into common site file
    print("\nWriting site XML file")

    xml = ET.Element("ldndcsite")
    for scnt, site in enumerate(sites):
        x = site.xml.find("description")
        if scnt == 0:
            xml.append(x)
        a = site.xml
        a.remove(x)
        xml.append(a)
    strOut = MD.parseString(ET.tostring(xml)).toprettyxml()
    open(outname, "w").write(strOut)

    if DEBUG:
        print("Writing netCDF file of selected regions:", outname[:-4] + ".nc")
        dout = xr.Dataset()

        # mask A
        da = xr.DataArray(mask, coords=[("lat", lats), ("lon", lons)])
        da.name = "selected mask"
        dout["selmask"] = da

        # clip to bbox
        if options.bbox:
            print(f"BBox: {options.bbox}")
            lon1, lat1, lon2, lat2 = (
                float(x)
                for x in options.bbox.replace("[", "").replace("]", "").split(",")
            )
            lat1, lat2 = (lat1, lat2) if lat1 < lat2 else (lat2, lat1)
            lon1, lon2 = (lon1, lon2) if lon1 < lon2 else (lon2, lon1)
            dout = dout.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))

        da2 = xr.DataArray(ids, coords=[("lat", lats), ("lon", lons)])
        da2.name = "ids"
        dout["ids"] = da2

        dout.to_netcdf(outname[:-4] + ".nc", format="NETCDF4_CLASSIC")