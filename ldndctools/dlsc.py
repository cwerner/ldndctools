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

import logging
import os
from importlib import resources
from pathlib import Path

import intake
import numpy as np
from pydantic import ValidationError
from tqdm import tqdm

from ldndctools.cli.cli import cli
from ldndctools.cli.selector import ask_for_resolution, CoordinateSelection, Selector
from ldndctools.extra import get_config, set_config
from ldndctools.misc.create_data import create_dataset
from ldndctools.misc.types import BoundingBox, RES
from ldndctools.sources.soil.soil_iscricwise import ISRICWISE_SoilDataset

log = logging.getLogger(__name__)

log.setLevel("DEBUG")

NODATA = "-99.99"

# TODO: there has to be a better way here...
#       also, tqdm takes no effect
with resources.path("data", "") as dpath:
    DPATH = Path(dpath)


def main():
    # parse args
    args = cli()

    # read config
    cfg = get_config(args.config)

    # write config
    if args.storeconfig:
        set_config(cfg)

    # def _get_cfg_item(group, item, save="na"):
    #     return cfg[group].get(item, save)

    # TODO: move this to file
    # BASEINFO = dict(
    #     AUTHOR=_get_cfg_item("info", "author"),
    #     EMAIL=_get_cfg_item("info", "email"),
    #     DATE=str(datetime.datetime.now()),
    #     DATASET=_get_cfg_item("project", "dataset"),
    #     VERSION=_get_cfg_item("project", "version", save="0.1"),
    #     SOURCE=_get_cfg_item("project", "source"),
    # )

    if (args.rcode is not None) or (args.file is not None):
        log.info("Non-interactive mode...")
        cfg["interactive"] = False

    # query environment or command flags for selection (non-interactive mode)
    args.rcode = os.environ.get("DLSC_REGION", args.rcode)
    rcode = args.rcode.split("+") if args.rcode else None

    if not RES.contains(args.resolution):
        log.error(f"Wrong resolution: {args.resolution}. Use HR, MR or LR.")
        exit(-1)

    res = RES[args.resolution]

    bbox = None
    if args.bbox:
        x1, y1, x2, y2 = [float(x) for x in args.bbox.split(",")]
        try:
            bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
        except ValidationError:
            print("Ilegal bounding box coordinates specified.")
            print("required: x1,y1,x2,y2 [cond: x1<x2, y1<y2]")
            print(f"given:    x1={x1},y1={y1},x2={x2},y2={y2}")
            exit(1)

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

    res_scale_mapper = {RES.LR: 50, RES.MR: 50, RES.HR: 10}

    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    df = catalog.admin(scale=res_scale_mapper[res]).read()
    soil_raw = catalog.soil(res=res.name).read()

    soil = ISRICWISE_SoilDataset(soil_raw)

    if args.file:
        selector = CoordinateSelection(args.file)
    else:
        selector = Selector(df)

    if args.interactive:
        res = ask_for_resolution(cfg)
        selector.ask()
    else:
        if rcode:
            selector.set_region(rcode)

    if bbox:
        log.info(f"Setting bounding box to {bbox}")
        selector.set_bbox(bbox)
    else:
        if isinstance(selector, Selector):
            log.info("Adjusting bounding box to selection extent")
            extent = selector.gdf_mask.bounds.iloc[0]

            new_bbox = BoundingBox(
                x1=np.floor(extent.minx).astype("float").item(),
                x2=np.ceil(extent.maxx).astype("float").item(),
                y1=np.floor(extent.miny).astype("float").item(),
                y2=np.ceil(extent.maxy).astype("float").item(),
            )
            selector.set_bbox(new_bbox)

    log.info(selector.selected)

    with tqdm(total=1) as progressbar:
        xml, nc = create_dataset(soil, selector, res, progressbar)

    open(cfg["outname"], "w").write(xml)
    ENCODING = {
        "siteid": {"dtype": "int32", "_FillValue": -1, "zlib": True},
        "soilmask": {"dtype": "int32", "_FillValue": -1, "zlib": True},
    }
    nc.to_netcdf(cfg["outname"].replace(".xml", ".nc"), encoding=ENCODING)


if __name__ == "__main__":
    main()
