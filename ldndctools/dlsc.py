#!/usr/bin/env python3
# Dynamic LandscapeDNDC Sitefile Creator (DLSC)
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
import logging
import os, datetime, shutil, string, math
import progressbar as pb
from pathlib import Path
import xml.dom.minidom as MD
import xml.etree.cElementTree as ET

from ldndctools import __version__

from .cli import cli
from .extra import get_config, set_config
from .misc.xmlclasses import SiteXML

log = logging.getLogger(__name__)

log.setLevel("DEBUG")

NODATA = "-99.99"

DPATH = Path("data")


def translateDataFormat(d):
    """ translate data from nc soil file (pointwise xarray sel) to new naming and units """
    data = []
    ks = nmap.keys()
    for l in range(len(d.lev)):
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

    vals, keys, t = [], [], []

    for i in range(len(labels[0])):
        for j in range(len(labels)):
            la = i * len(labels) + j + base
            if labels[j, i] != "":
                vals.append(labels[j, i])
                labels[j, i] = f"[{la}] {labels[j, i]}"
                keys.append(la)

    for row in labels:
        t.append("".join([x.ljust(35) for x in row]))

    print("\n".join(t) + "\n")


def main():
    # parse args
    args = cli()

    # read config
    cfg = get_config(args.config)

    # write config
    if args.storeconfig:
        set_config(cfg)

    def _get_cfg_item(group, item, save="na"):
        return cfg[group].get(item, save)

    BASEINFO = dict(
        AUTHOR=_get_cfg_item("info", "author"),
        EMAIL=_get_cfg_item("info", "email"),
        DATE=str(datetime.datetime.now()),
        DATASET=_get_cfg_item("project", "dataset"),
        VERSION=_get_cfg_item("project", "version", save="0.1"),
        SOURCE=_get_cfg_item("project", "source"),
    )

    INTERACTIVE = True

    if (args.rcode is not None) or (args.ccode is not None) or (args.file is not None):
        log.info("Non-interactive mode...")
        INTERACTIVE = False

    # query environment or command flags for selection (non-intractive mode)
    args.rcode = os.environ.get("DLSC_REGION", args.rcode)
    args.ccode = os.environ.get("DLSC_COUNTRY", args.ccode)

    # single country selection
    if (args.rcode is None) and (args.ccode is not None):
        args.rcode = "c"

    dres = dict(LR="0.5x0.5deg", MR="0.25x0.25deg", HR="0.0833x0.0833deg")

    if args.resolution in ["LR", "MR", "HR"]:
        SOIL = DPATH / "soil" / f"GLOBAL_WISESOIL_S1_{args.resolution}.nc"
        ADMIN = DPATH / "tmworld" / f"tmworld_{args.resolution}.nc"
        resStr = dres[args.resolution]
    else:
        log.error(f"Wrong resolution: {args.resolution}. Use HR, MR or LR.")
        exit(-1)

    if not args.outfile:
        outname = f"sites_{args.resolution}.xml"
    else:
        outname = args.outfile
        if ("LR" not in outname) and ("HR" not in outname) and ("MR" not in outname):
            if outname.endswith(".xml"):
                outname = f"{outname[:-4]}_{args.resolution}.xml"
            else:
                outname = f"{outname}_{args.resolution}.xml"

    log.info(f"Soil resolution: {args.resolution} [{resStr}]")
    log.info(f"Outfile name:    {outname}")

    # get cell mask from soil/ admin intersect
    dss = xr.open_dataset(SOIL).sel(lev=1)["PROP1"]
    soilmask = np.ma.where(dss.to_masked_array() > 0, 1, 0)

    # countries
    df = pd.read_csv(DPATH / "tmworld" / "tmworld_full_lut.txt", sep="\t")

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
    dfr = pd.read_csv(DPATH / "tmworld" / "tmworld_regions_lut.txt", sep="\t")
    Dregions = dict(zip(dfr.R_Name, dfr.R_Code))

    # subregions
    dfsr = pd.read_csv(DPATH / "tmworld" / "tmworld_subregions_lut.txt", sep="\t")
    Dsubregions = dict(zip(dfsr.SR_Name, dfsr.SR_Code))

    # lists with selection ids for tmworld netcdfs
    UNR, UNSR, UNC = [], [], []

    # special flags (TODO: cleanup later)
    eu28, world = False, False

    if args.rcode:
        UNR.append(args.rcode)
    if args.ccode:
        UNC.append(args.ccode)

    if INTERACTIVE:

        print("\nPlease select your region/ country [use codes]:")
        print('Multiple selections allowed [i.e. "12+13+17"]\n')
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
            if args.rcode in [None]:
                x = input("Select (sub-)region (multiple: +; c: add countries): ")
            else:
                x = args.rcode

            if x == "":
                showCountries = True
                break

            items = x.split("+") if "+" in x else [x]
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
                            print(f"Invalid Entry (0...{len(seq1)+len(seq2)-1}) {I}")

                    except ValueError:
                        print("Invalid Entry")

        # create human-readable selection lists
        selPrint1, selPrint2 = [], []
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
                if args.ccode is None:
                    x = input("Select country (multiple: +): ")
                else:
                    x = args.ccode

                items = x.split("+") if "+" in x else [x]

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

        log.info("----------------------------------")
        log.info("Selection")
        if len(selPrint1) > 0:
            log.info(f"Region  : {';'.join(selPrint1)}")
        if len(selPrint2) > 0:
            log.info(f"Country : {';'.join(selPrint2)}")

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

    with xr.open_dataset(ADMIN) as ds:
        lats, lons = ds.lat.values, ds.lon.values

        # init empty mask
        mask = np.zeros_like(ds.UN.values)

        # use coords from file
        if args.file:
            mask = createMask_fromfile(ds.UN, args.file)

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

    log.info("Number of sites/ cells:")
    log.info(f" region mask: {int(np.sum(mask))}")
    mask *= soilmask
    log.info(f" + soil mask: {int(np.sum(mask))}")
    log.info("----------------------------------")

    ids = np.zeros_like(mask)

    if world and args.resolution == "HR":
        log.warn("\nWARNING  You selected the entire world in high-res as a domain.")
        log.warn("         This will take a loooooooooong time.\n")
        x = raw_input("[p] to proceed, anything else to abort")

        if string.lower(x) != "p":
            exit(1)

    # MAIN LOOP
    # iterate over mask to build XML
    ds = xr.open_dataset(SOIL)

    Lcids, Lix, Ljx = [], [], []
    Dcids = {}

    # cid mode LR: 1000, MR/HR: 10000
    M = 10000 if args.resolution in ["HR", "MR"] else 1000

    LATS = ds.coords["lat"].values

    for j in range(len(mask)):
        for i in range(len(mask[0])):
            if mask[j, i] == 1:
                cid = ((len(mask) - 1) - j) * M + i if LATS[0] < LATS[-1] else j * M + i
                ids[j, i] = cid
                Lcids.append(cid)
                Lix.append(i)
                Ljx.append(j)
                Dcids[(LATS[j], ds.coords["lon"].values[i])] = cid

    CHUCK = 200

    def create_chunks(l):
        return [l[i : i + CHUCK] for i in range(0, len(l), CHUCK)]

    Lcids2d = create_chunks(Lcids)
    Lix2d = create_chunks(Lix)
    Ljx2d = create_chunks(Ljx)

    sites = []
    sbCnt = 1
    cnt = 0

    bar = pb.ProgressBar(
        maxval=len(Lcids),
        term_width=80,
        widgets=[
            pb.Bar("=", " %s [" % "Status: extracting sites", "]"),
            " ",
            pb.SimpleProgress(),
            " ",
            pb.Percentage(),
        ],
    ).start()

    # regional subset first to savetime
    min_lat, max_lat = ds.lat.isel(lat=min(Ljx)), ds.lat.isel(lat=max(Ljx))
    min_lon, max_lon = ds.lon.isel(lon=min(Lix)), ds.lon.isel(lon=max(Lix))
    min_dlat, min_dlon = min(Ljx), min(Lix)

    ds_ = ds.sel(lat=slice(min_lat, max_lat), lon=slice(min_lon, max_lon))

    for Lix, Ljx, Lcids in zip(Lix2d, Ljx2d, Lcids2d):
        log.debug(f"processing site batch {sbCnt} of {len(Lcids2d)}")

        dx = ds_.isel(
            lat=xr.DataArray(np.array(Ljx) - min_dlat, dims="points"),
            lon=xr.DataArray(np.array(Lix) - min_dlon, dims="points"),
        )

        for dp in dx.points:
            d = dx.sel(points=dp)
            _lat, _lon = float(d.lat), float(d.lon)
            site = SiteXML(lat=_lat, lon=_lon, id=Dcids[(_lat, _lon)], **BASEINFO)

            # take point selection and return dict with modified data naming and units
            data2 = translateDataFormat(d)

            addFlag = False
            if data2[0]["topd"] >= 0.0 and (
                (data2[0]["botd"] - data2[0]["topd"]) * 10 > 0
            ):
                addFlag = True

            # 5 layers !!!
            for lay in range(5):
                if data2[lay]["topd"] >= 0.0:
                    data2[lay]["depth"] = (data2[lay]["botd"] - data2[lay]["topd"]) * 10
                    if lay in [0, 1]:
                        split = 10
                    elif lay in [2, 3]:
                        split = 4
                    else:
                        split = 2
                    data2[lay]["split"] = split

                    # default iron percentage
                    data2[lay]["iron"] = 0.01

                    data2[lay].pop("topd")
                    data2[lay].pop("botd")

                    if lay == 0 and args.extrasplit:
                        site.addSoilLayer(
                            data2[lay],
                            litter=False,
                            accuracy=cmap,
                            extra_split=args.extrasplit,
                        )
                    else:
                        site.addSoilLayer(data2[lay], litter=False, accuracy=cmap)

            if addFlag == True:
                sites.append(site)

            bar.update(cnt)
            cnt += 1

        sbCnt += 1

    # end bar
    bar.finish()

    # write XML file
    # merge site chunks into common site file
    log.info("Writing site XML file")

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

    if log.level == logging.DEBUG:
        log.info(f"Writing netCDF file of selected regions:{outname[:-4]}.nc")
        dout = xr.Dataset()

        # mask A
        da = xr.DataArray(mask, coords=[("lat", lats), ("lon", lons)])
        da.name = "selected mask"
        dout["selmask"] = da

        # clip to bbox
        if args.bbox:
            log.debug(f"netcdf with custom bounding box {args.bbox}")
            lon1, lat1, lon2, lat2 = (
                float(x) for x in args.bbox.replace("[", "").replace("]", "").split(",")
            )
            lat1, lat2 = (lat1, lat2) if lat1 < lat2 else (lat2, lat1)
            lon1, lon2 = (lon1, lon2) if lon1 < lon2 else (lon2, lon1)
            dout = dout.sel(lat=slice(lat1, lat2), lon=slice(lon1, lon2))
        elif args.bboxoff:
            log.debug("netcdf without bounding box")
        else:
            log.debug(f"netcdf with auto bounding box")

            # find a suitable bbox from mask
            def find_bbox(mask):
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                rmin, rmax = np.where(rows)[0][[0, -1]]
                cmin, cmax = np.where(cols)[0][[0, -1]]
                return rmin, rmax, cmin, cmax

            rmin, rmax, cmin, cmax = find_bbox(mask)
            dout = dout.isel(lat=slice(rmin, rmax + 1), lon=slice(cmin, cmax + 1))

        da2 = xr.DataArray(ids, coords=[("lat", lats), ("lon", lons)], name="ids")
        dout[da2.name] = da2

        dout.to_netcdf(outname[:-4] + ".nc", format="NETCDF4_CLASSIC")


if __name__ == "__main__":
    main()
