import logging
from typing import Iterable

import geopandas as gpd
import pandas as pd
import questionary
from questionary.prompts.common import Choice, Separator
from shapely.geometry import Polygon

from ldndctools.misc.types import BoundingBox, RES

logging.getLogger("fiona").setLevel(logging.WARNING)


def clean_results(x):
    return [r for r in x if r != "BACK"]


# TODO: this should be moved elsewhere
def ask_for_region(self):
    """ask user for region to select (2-step process)"""

    selection = ["BACK"]
    choices = []
    while "BACK" in selection:
        response = questionary.select(
            "Select area by (you can go back and combine these choices):",
            choices=["continents", "regions", "countries"],
        ).ask()

        selection_items = getattr(self, response)
        if response == "regions":
            choices = (
                [Choice(r) for r in selection_items if "EU" in r]
                + [Separator()]
                + [Choice(r) for r in selection_items if "EU" not in r]
            )
        else:
            choices = [Choice(r) for r in selection_items.keys()]

        # preselect previous choices
        for choice in choices:
            if choice.value in selection:
                choice.checked = True

        current_selection = questionary.checkbox("Please select", choices=choices).ask()
        selection = selection + current_selection
        if "BACK" not in current_selection:
            selection = clean_results(selection)
        print(f"Selection: {clean_results(selection)}")

    selection = list(set(clean_results(selection)))

    return self.extract_countries(selection)


def ask_for_resolution(cfg):
    """ask use for a target resolution if not provided via command line"""

    disabled = True if hasattr(cfg, "res") else False
    return (
        questionary.select(
            "Select output resolution:",
            choices=[Choice(r.value, r) for r in RES.members()],
        )
        .skip_if(disabled, default=RES.LR)
        .ask()
    )


class Selector(object):
    def __init__(self, df):
        self._df = df[~df.ADM0_A3.isin(["ATF", "ATA"])]
        self._df = self._df.set_crs("EPSG:4326")

        # add all to initial selection
        countries = sorted(self._df.ADM0_A3.unique())
        self._selection = {
            c: self._df.query(f"ADM0_A3=='{c}'").ADMIN.values[0] for c in countries
        }

        self._bbox = BoundingBox()
        self._names = sorted(self._df.ADM0_A3.unique())

    def extract_countries(self, selection):
        # merge countries of (potentially) multiple regions
        countries = {}
        for sel in selection:
            for response in ["continents", "regions", "countries"]:
                z = getattr(self, response)
                if response != "countries":
                    if sel in z.keys():
                        countries.update(z[sel])
                else:
                    if sel in z.keys():
                        countries.update({sel: z[sel]})
        return countries

    @property
    def continents(self):
        data = {}
        for continent, _df in self._df.groupby("CONTINENT"):
            countries = sorted(_df.ADM0_A3.unique())
            data[continent] = {
                c: _df.query(f"ADM0_A3=='{c}'").ADMIN.values[0] for c in countries
            }
        return data

    @property
    def regions(self):
        data = {}
        for region, _df in self._df.groupby("REGION_UN"):
            countries = sorted(_df.ADM0_A3.unique())
            data[region] = {
                c: _df.query(f"ADM0_A3=='{c}'").ADMIN.values[0] for c in countries
            }

        for region, _df in self._df.groupby("SUBREGION"):
            countries = sorted(_df.ADM0_A3.unique())
            data[region] = {
                c: _df.query(f"ADM0_A3=='{c}'").ADMIN.values[0] for c in countries
            }

        # extra
        # NOTE: MLT is missing in LR dataset
        eu27_codes = [
            "AUT",
            "BEL",
            "BGR",
            "CYP",
            "CZE",
            "DEU",
            "DNK",
            "ESP",
            "EST",
            "FIN",
            "FRA",
            "GRC",
            "HRV",
            "HUN",
            "IRL",
            "ITA",
            "LTU",
            "LUX",
            "LVA",
            "MLT",
            "NLD",
            "POL",
            "PRT",
            "ROU",
            "SVK",
            "SVN",
            "SWE",
        ]

        eu28_codes = sorted(eu27_codes + ["GBR"])
        eu28plus_codes = sorted(eu27_codes + ["GBR", "CHE", "NOR"])

        def get_name(df, country_code):
            try:
                return df.query(f"ADM0_A3=='{country_code}'").ADMIN.values[0]
            except ValueError:
                pass

        data["EU27"] = {
            c: get_name(self._df, c) for c in eu27_codes if c in self._names
        }
        data["EU28"] = {
            c: get_name(self._df, c) for c in eu28_codes if c in self._names
        }
        data["EU28PLUS"] = {
            c: get_name(self._df, c) for c in eu28plus_codes if c in self._names
        }

        return dict(sorted(data.items()))

    def set_bbox(self, bbox: BoundingBox) -> None:
        self._bbox = bbox

    def set_region(self, region: Iterable[str]) -> None:
        self._selection = self.extract_countries(region)

    @property
    def countries(self):
        return {
            c: self._df.query(f"ADM0_A3=='{c}'").ADMIN.values[0]
            for c in sorted(self._df.ADM0_A3.unique())
        }

    @property
    def selected(self):
        return self._selection

    @property
    def gdf(self):
        return (
            self._df.loc[self._df.ADM0_A3.isin(list(self.selected.keys()))]
            if len(self.selected) > 0
            else None
        )

    @property
    def gdf_mask(self):
        if self.gdf is not None:
            x1, x2, y1, y2 = self._bbox.x1, self._bbox.x2, self._bbox.y1, self._bbox.y2
            bbox_poly = Polygon([(x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)])
            bbox = gpd.GeoDataFrame([1], geometry=[bbox_poly], crs=self.gdf.crs)

            df = self.gdf.assign(dummy=0)
            gdf_mask = gpd.clip(df.dissolve(by="dummy").loc[:, ["geometry"]], bbox)
            if len(gdf_mask) > 0:
                return gdf_mask
        return None

    def ask(self):
        self._selection = ask_for_region(self)


class CoordinateSelection:
    def __init__(self, infile, lon_col="lon", lat_col="lat", id_col="ID"):
        df = pd.read_csv(infile, delim_whitespace=True)

        self.lons = df[lon_col].values
        self.lats = df[lat_col].values
        self.ids = (
            df[id_col].values if id_col in list(df.columns) else range(len(self.lats))
        )

    @property
    def selected(self):
        return dict({k: (v1, v2) for v1, v2, k in zip(self.lons, self.lats, self.ids)})
