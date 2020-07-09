import geopandas as gpd
import xarray as xr
import urllib
from pathlib import Path
import questionary
from questionary import form
from questionary.prompts.common import Choice, Separator
from questionary import Validator, ValidationError


DATA = Path.home() / ".ldndctools" / "data"


def invert_dict(d):
    return {v: k for k, v in d.items()}


def shrink_dataarray(da, dims=None):
    """remove nodata borders from spatial dims of dataarray"""
    dims = set(dims) if dims else set(da.dims)

    if len(dims) != 2:
        raise IndexError

    # non-spatial dims (carry over, only shrink spatial dims)
    nsd = set(da.dims) - dims
    nsd_indexers = {d: range(len(da[d])) for d in nsd}

    indexers = {
        d: (da.count(dim=dims - set([d]) | nsd).cumsum() != 0)
        * (da.count(dim=dims - set([d]) | nsd)[::-1].cumsum()[::-1] != 0)
        for d in dims
    }

    indexers.update(nsd_indexers)

    return da.isel(**indexers)


def ask_for_resolution(cfg):
    """ask use for a target resolution if not provided via command line"""

    res = {
        "LR": "low res.    [0.5 x 0.5 deg]",
        "MR": "medium res. [0.25 x 0.25 deg]",
        "HR": "high res.   [0.083 x 0.083 deg]",
    }

    DISABLED = True if cfg.res else False
    return (
        questionary.select(
            "Select output resolution:",
            choices=[Choice(k, v) for k, v in invert_dict(res).items()],
        )
        .skip_if(DISABLED, default="LR")
        .ask()
    )


def remove_brackets(s):
    s = s.strip()
    if len(s) > 2:
        for start_bracket, end_bracket in zip("([{", ")]}"):
            if (s[0] == start_bracket) and (s[-1] == end_bracket):
                return s[1:-1]
    return s


class BBoxValidator(Validator):
    def validate(self, document):
        ok = validate_bbox(document.text)
        if not ok:
            raise ValidationError(
                message="Correct format: '[X1, Y1, X2, Y2]'",
                cursor_position=len(document.text),
            )  # Move cursor to end


def validate_bbox(s):
    s = remove_brackets(s)

    if s == "":
        return True

    # validate number of coordinate values
    bbox_coords = s.split(",")
    if len(bbox_coords) != 4:
        return False

    # validate coodinate ordering
    try:
        bbox_coords = [float(x) for x in bbox_coords]
    except ValueError:
        return False

    x1, y1, x2, y2 = bbox_coords
    if x1 == x2 or y1 == y2:
        return False
    for lon in [x1, x2]:
        if lon < -180 or lon > 180:
            return False
    for lat in [y1, y2]:
        if lat < -90 or lat > 90:
            return False

    return True


def ask_for_bbox(cfg):
    """ask for a bounding box"""

    DISABLED = True if cfg.bbox else False
    return (
        questionary.text("Select (optional) bounding box:", validate=BBoxValidator)
        .skip_if(DISABLED, default="[-180,-90,180,90]")
        .ask()
    )


def ask_for_region(self):
    """ask user for region to select (2-step process)"""

    response = questionary.select(
        "Select area by:", choices=["continents", "regions", "countries"],
    ).ask()

    x = getattr(self, response)
    if response == "regions":
        choices = (
            [Choice(r) for r in x if "EU" in r]
            + [Separator()]
            + [Choice(r) for r in x if not "EU" in r]
        )
    else:
        choices = [Choice(r) for r in x.keys()]

    # preselect first selection item
    choices[0].checked = True

    selection = questionary.checkbox("Please select", choices=choices).ask()

    # merge countries of (potentially) multiple regions
    countries = {}
    print(selection)
    for c in [getattr(self, response)[k] for k in selection]:
        print(c)
        countries.update(c)

    return countries


class Selector(object):
    def __init__(self, df):
        self._df = df[~df.ADM0_A3.isin(["ATF", "ATA"])]
        self._selection = None
        self._bbox = [-180, -90, 180, 90]
        self._names = sorted(self._df.ADM0_A3.unique())

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
        eu27 = [
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

        eu28 = sorted(eu27 + ["GBR"])
        eu28p = sorted(eu27 + ["GBR", "CHE", "NOR"])

        def get_name(df, country_code):
            return df.query(f"ADM0_A3=='{country_code}'").ADMIN.values[0]

        for k, source in zip(["EU27", "EU28", "EU28+"], [eu27, eu28, eu28p]):
            data[k] = {c: get_name(self._df, c) for c in source if c in self._names}

        return dict(sorted(data.items()))

    @property
    def countries(self):
        return {
            c: self._df.query(f"ADM0_A3=='{c}'").ADMIN.values[0]
            for c in sorted(self._df.ADM0_A3.unique())
        }

    @property
    def selection(self):
        return self._selection

    @property
    def boundingbox(self):
        return self._bbox

    def ask(self):
        self._selection = ask_for_region(self)

    def show(self, sel="continents", show_names=False):
        if sel not in ["continents", "regions", "countries"]:
            raise ValueError

        if sel == "countries":
            abbrev, names = zip(*getattr(self, sel).items())
            if show_names:
                print(", ".join(names))
        else:
            for key, values in getattr(self, sel).items():
                abbrev, names = zip(*values.items())
                if show_names:
                    print(key, ":\n", ", ".join(names))
                else:
                    print(key, ",".join(values))


def create_data_path(DATA):
    DATA.mkdir(parents=True, exist_ok=True)


def download_zipfile_from_url(url, filename):
    with urllib.request.urlopen(url) as dl_file:
        with open(filename, "wb") as out_file:
            out_file.write(dl_file.read())


def load_world_dataframe(res="LR"):
    urls = {"HR": 10, "MR": 50, "LR": 110}

    if res not in urls:
        raise ValueError

    create_data_path(DATA)

    DATAFILE = DATA / f"ne_{urls[res]}m_admin_0_countries.zip"
    url = f"https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/{urls[res]}m/cultural/ne_{urls[res]}m_admin_0_countries.zip"
    if not DATAFILE.is_file():
        print(f"downloading {url}")
        download_zipfile_from_url(url, DATAFILE)
    return gpd.read_file(f"zip://{DATAFILE}")


if __name__ == "__main__":

    # simulate commandline cfg
    class cfg:
        pass

    cfg.res = "LR"
    cfg.bbox = [-10, 30, 40, 70]

    resolution = ask_for_resolution(cfg)
    bbox = ask_for_bbox(cfg)

    df = load_world_dataframe(res=resolution)

    # region selection
    selector = Selector(df)
    selector.ask()

    print(selector.selection)
