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

import sys

if sys.version_info >= (3, 7):
    from importlib import resources
else:
    import importlib_resources as resources

import xarray as xr

import numpy as np
import pandas as pd
import logging
import os
import datetime
from pathlib import Path

import intake

from tqdm import tqdm

from ldndctools.cli.cli import cli
from ldndctools.cli.selector import Selector
from ldndctools.extra import get_config, set_config
from ldndctools.misc.types import RES
from ldndctools.misc.create_data import create_dataset

log = logging.getLogger(__name__)

log.setLevel("DEBUG")

NODATA = "-99.99"

# TODO: there has to be a better way here...
#       also, tqdm takes no effect
with resources.path("data", "") as dpath:
    DPATH = Path(dpath)


def find_nearest(a, a0):
    """find nearest lat or lon value from coord"""
    return a.flat[np.abs(a - a0).argmin()]


def createMask_fromfile(ds, infile):
    df = pd.read_csv(infile, delim_whitespace=True)
    ds_x = xr.zeros_like(ds)
    ds_id = xr.ones_like(ds, dtype="int") * np.nan if "ID" in df.columns else None

    for _, r in df.iterrows():
        _lon = find_nearest(ds.lon.values, r.lon)
        _lat = find_nearest(ds.lat.values, r.lat)
        ds_x.loc[dict(lon=_lon, lat=_lat)] = 1
        if "ID" in df.columns:
            ds_id.loc[dict(lon=_lon, lat=_lat)] = r.ID
    ds_x = ds_x.values
    if "ID" in df.columns:
        ds_id = ds_id.values
    return ds_x, ds_id


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

    cfg["interactive"] = True

    if (args.rcode is not None) or (args.ccode is not None) or (args.file is not None):
        log.info("Non-interactive mode...")
        cfg["interactive"] = False

    # query environment or command flags for selection (non-interactive mode)
    args.rcode = os.environ.get("DLSC_REGION", args.rcode)
    args.ccode = os.environ.get("DLSC_COUNTRY", args.ccode)

    if not RES.has_key(args.resolution):
        log.error(f"Wrong resolution: {args.resolution}. Use HR, MR or LR.")
        exit(-1)

    res = RES[args.resolution]

    if not args.outfile:
        cfg["outname"] = f"sites_{res.name}.xml"
    else:
        cfg["outname"] = args.outfile
        if all([x.value not in cfg["outname"] for x in RES.members()]):
            if cfg["outname"].endswith(".xml"):
                cfg["outname"] = f'{cfg["outname"][:-4]}_{res.name}.xml'
            else:
                cfg["outname"] = f'{cfg["outname"]}_{res.name}.xml'

    log.info(f"Soil resolution: {res.name} {res.value}")
    log.info(f'Outfile name:    {cfg["outname"]}')

    rmap = {RES.LR: 50, RES.MR: 50, RES.HR: 10}

    ## # resolution
    ## resolution = ask_for_resolution(cfg)

    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    df = catalog.admin(res=rmap[res]).read()
    soil = catalog.soil(res=res.name).read()

    # region selection
    selector = Selector(df)
    selector.ask()

    with tqdm(total=1) as progressbar:
        result = create_dataset(soil, selector, res, progressbar)

    xml, nc = result

    open(cfg["outname"], "w").write(xml)
    nc.to_netcdf(cfg["outname"].replace(".xml", ".nc"))


if __name__ == "__main__":
    main()
