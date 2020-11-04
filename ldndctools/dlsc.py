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

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

import intake
import numpy as np
import pandas as pd
import xarray as xr
from omegaconf import OmegaConf
from tqdm import tqdm

from ldndctools.cli.cli import cli
from ldndctools.cli.selector import Selector, ask_for_resolution
from ldndctools.misc.create_data import create_dataset
from ldndctools.misc.types import RES, BoundingBox

log = logging.getLogger(__name__)

log.setLevel("DEBUG")

NODATA = "-99.99"

# TODO: there has to be a better way here...
#       also, tqdm takes no effect
with resources.path("data", "") as dpath:
    DPATH = Path(dpath)


def find_config(cli_config_path: Optional[Union[Path, str]]) -> Optional[Path]:
    """look for config file in default locations"""
    locations = [
        Path(cli_config_path) if cli_config_path else None,
        os.environ.get("LDNDCTOOLS_CONF"),
        Path.cwd(),
        Path.home(),
        "/etc/ldndctools",
    ]
    locations = [x for x in locations if x]

    for loc in locations:
        f = loc / "ldndctools.conf"
        if f.is_file():
            return f
    return None


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

    # read config from cli - otherwise use default from package
    cfg_filename = find_config(args.config)
    file_cfg = OmegaConf.load(cfg_filename)

    log.info(OmegaConf.to_yaml(file_cfg))

    # run config (possibly from yaml or cli)

    @dataclass
    class RunConfig:
        bbox: Iterable[float] = (-180, -90, 180, 90)
        extrasplit: bool = False
        interactive: bool = False
        resolution: str = "HR"
        outfile: str = "sites.xml"
        rcode: Iterable[str] = ()
        verbose: bool = False

    cli_cfg = OmegaConf.structured(RunConfig)

    # overwrite defaults with cli args
    cli_cfg.interactive = args.interactive
    cli_cfg.extrasplit = args.extrasplit
    cli_cfg.resolution = args.resolution
    cli_cfg.verbose = args.verbose

    # ... and optional args
    if args.bbox:
        log.info(args.bbox)
        cli_cfg.bbox = [float(x) for x in args.bbox.split(",")]
    if args.outfile:
        cli_cfg.outfile = args.outfile
    if args.rcode:
        cli_cfg.rcode = args.rcode.split("+")

    # merge configs
    cfg = OmegaConf.merge(file_cfg, cli_cfg)
    log.info(OmegaConf.to_yaml(cfg))

    # query environment or command flags for selection (non-interactive mode)
    rcode = cfg.rcode if len(cfg.rcode) > 0 else None

    if not RES.contains(cfg.resolution):
        log.error(f"Wrong resolution: {cfg.resolution}. Use HR, MR or LR.")
        exit(-1)

    res = RES[cfg.resolution]
    x1, y1, x2, y2 = cfg.bbox
    bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)

    # validate outfile naming convention...
    # TODO: refactor this out
    if all([x.name not in cfg.outfile for x in RES.members()]):
        log.info([x.name for x in RES.members()])
        if cfg.outfile.endswith(".xml"):
            cfg.outfile = f"{cfg.outfile[:-4]}_{res.name}.xml"
        else:
            cfg.outfile = f"{cfg.outfile}_{res.name}.xml"

    log.info(f"Soil resolution: {res.name} {res.value}")
    log.info(f"Outfile name:    {cfg.outfile}")

    res_scale_mapper = {RES.LR: 50, RES.MR: 50, RES.HR: 10}

    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    df = catalog.admin(scale=res_scale_mapper[res]).read()
    soil = catalog.soil(res=res.name).read()

    selector = Selector(df)

    if cfg.interactive:
        res = ask_for_resolution()
        selector.ask()
    else:
        if rcode:
            selector.set_region(rcode)

    if bbox:
        log.info(f"Setting bounding box to {bbox}")
        selector.set_bbox(bbox)
    else:
        log.info("Adjusting bounding box to selection extent")
        extent = selector.gdf_mask.bounds.iloc[0]

        new_bbox = BoundingBox(
            x1=np.floor(extent.minx).astype("int").item(),
            x2=np.ceil(extent.maxx).astype("int").item(),
            y1=np.floor(extent.miny).astype("int").item(),
            y2=np.ceil(extent.maxy).astype("int").item(),
        )
        selector.set_bbox(new_bbox)

    log.info(selector.selected)

    with tqdm(total=1) as progressbar:
        result = create_dataset(soil, selector, res, progressbar)

    xml, nc = result

    open(cfg.outfile, "w").write(xml)
    nc.to_netcdf(cfg.outfile.replace(".xml", ".nc"))


if __name__ == "__main__":
    main()
