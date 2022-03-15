import gzip
import io
from dataclasses import asdict, dataclass
from importlib import resources
from typing import Any, Dict, Optional

import dask
import intake
import numpy as np
import pandas as pd
import urllib3
import xarray as xr
from dask.distributed import Client

from ldndctools.misc.geohash import coords2geohash_dec
from ldndctools.misc.types import BoundingBox

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class ClimateSiteStats:
    id: int
    latitude: float
    longitude: float

    wind_speed: float
    annual_precipitation: float
    temperature_average: float
    temperature_amplitude: float

    elevation: Optional[int] = -1
    cloudiness: Optional[float] = 0.5
    rainfall_intensity: Optional[float] = 5.0


def subset_climate_data(
    *, bbox: BoundingBox, time_min: Optional[str] = None, time_max: Optional[str] = None
) -> xr.Dataset:

    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))
        ds = catalog["climate_era5land_hr"].to_dask()
        ds = ds.sel(lat=slice(bbox.y1, bbox.y2), lon=slice(bbox.x1, bbox.x2))

        if time_min:
            ds = ds.sel(time=slice(time_min, None))

        if time_max:
            ds = ds.sel(time=slice(None, time_max))

    return ds


def amplitude(da):
    return (da.max(dim="time") - da.min(dim="time")) / 2


def fill_header_global(time):
    txt = f"""
%global
time     = "{time}/1"
%cuefile = "cuefile.txt"

"""
    return txt


def fill_header(data: ClimateSiteStats):

    txt = """
%climate
name = "climate_{id}.txt.gz"
archive = "ERA5 Land (resampled to LDNDC HR)"
id   = "{id}"

%attributes
elevation  = {elevation}
latitude   = {latitude:.6f}
longitude  = {longitude:.6f}

wind speed = {wind_speed:.2f}
cloudiness = {cloudiness:.1f}
rainfall intensity = {rainfall_intensity}

annual precipitation  = {annual_precipitation:.1f}
temperature average   = {temperature_average:.2f}
temperature amplitude = {temperature_amplitude:.2f}

%data
*       *       tavg    tmin    tmax    grad    prec    rh      wind
""".format(
        **asdict(data)
    )
    return txt


def writer(df: pd.DataFrame, pid: int, *, lookup: Dict[str, Any]):
    buffer = io.StringIO()
    print(">>>>>>>>>>>>>>")
    print(df.head(2))
    print(pid)
    print(len(list(lookup.keys())))
    print(">>>>>>>>>>>>>>")

    header_global = fill_header_global(df.time.min())
    buffer.write(header_global)

    dummy_data = ClimateSiteStats(
        id=942889503,
        latitude=30,
        longitude=30,
        wind_speed=10,
        annual_precipitation=1000,
        temperature_average=20,
        temperature_amplitude=10,
    )

    for geohash, gdf in df.groupby(df.index):
        data = lookup.get(geohash, dummy_data)
        # try:
        #     data = lookup[geohash]
        # except KeyError:
        #     continue

        # if data is None:
        #     continue

        # if hasattr(data, 'id') is False:
        #     continue

        header = fill_header(data)
        buffer.write(header)

        gdf = gdf.sort_values(by="time")

        cols = ["year", "jday", "tavg", "tmin", "tmax", "grad", "prec", "rh", "wind"]
        values = [
            gdf.time.dt.year,
            gdf.time.dt.dayofyear,
            gdf.tavg,
            gdf.tmin,
            gdf.tmax,
            gdf.rad,
            gdf.prec,
            gdf.rh,
            gdf.wind,
        ]

        fmt = "%-8.0f%-8.0f%-8.2f%-8.2f%-8.2f%-8.2f%-8.1f%-8.1f%-8.2f"
        np.savetxt(buffer, pd.DataFrame(dict(zip(cols, values))), fmt=fmt)

        buffer.write("\n\n")
    buffer.seek(0)

    with gzip.open(f"testdata/climdata-{pid:03}.txt.gz", "wt") as f:
        f.write(buffer.read())

    return None


# def inner(mask, lat, lon):
#     return -1 if np.isnan(mask) else coords2geohash_dec(lat=lat, lon=lon)


@np.vectorize
def inner(x, lat, lon):
    return -1 if np.isnan(x) else coords2geohash_dec(lat=lat, lon=lon)


def geohash_xr(mask):  # , lat, lon):
    data = xr.ones_like(mask, dtype=np.int64) * -1

    lats = np.tile(mask.lat.values, len(mask.lon.values)).reshape(mask.values.shape).T
    lons = np.tile(mask.lon.values, len(mask.lat.values)).reshape(mask.values.shape)
    data[:] = inner(mask, lats, lons)
    return data


def main():
    ds_vn = subset_climate_data(
        # bbox=BoundingBox(x1=101.5, x2=109.5, y1=8.0, y2=23.5),
        bbox=BoundingBox(x1=104.5, x2=105.5, y1=9.0, y2=10.0),
        # time_min='2000-01-01',
        # time_max='2002-12-31'
    )

    mask = xr.open_dataset("VN_MISC5_V2.nc")["rice_rot"]
    mask = xr.where(mask > 0, 1, np.nan).values

    tavg_year = ds_vn.tavg.groupby("time.year").mean(dim="time").mean(dim="year")
    tamp_year = ds_vn.tavg.groupby("time.year").apply(amplitude).mean(dim="year")
    prec_year = ds_vn.prec.groupby("time.year").sum(dim="time").mean(dim="year")
    wind_year = ds_vn.wind.groupby("time.year").mean(dim="time").mean(dim="year")

    stats = xr.Dataset()
    stats["tavg"] = tavg_year
    stats["tamp"] = tamp_year
    stats["prec"] = prec_year
    stats["wind"] = wind_year

    # stats["mask"] = xr.ones_like(stats.tavg)
    # stats["mask"][:] = mask

    stats["geohash"] = geohash_xr(stats.tavg)
    stats["geohash"].attrs["_FillValue"] = -1
    stats["geohash"].attrs["missing_value"] = -1

    # stats = stats.where(stats.mask == 1)

    # stats2 = stats.copy()
    # del stats["mask"]

    df_stats = (
        stats.to_dataframe()
        .dropna(subset=["tavg", "tamp", "wind"], how="all")
        .reset_index()
    )
    # ignore prec for now

    lookup = {}
    for _, row in df_stats.iterrows():
        # if row["geohash"] != -1:
        # geohash = coords2geohash_dec(lat=row["lat"], lon=row["lon"])
        lookup[int(row["geohash"])] = ClimateSiteStats(
            id=int(row["geohash"]),
            latitude=row["lat"],
            longitude=row["lon"],
            wind_speed=row["wind"],
            annual_precipitation=row["prec"],
            temperature_average=row["tavg"],
            temperature_amplitude=row["tamp"],
        )

    ds_vn["geohash"] = xr.ones_like(ds_vn.tavg.isel(time=0), dtype=np.int64)
    ds_vn["geohash"] = stats["geohash"]
    ds_vn = ds_vn.stack(location=("lat", "lon"))
    ds_vn = ds_vn.swap_dims({"location": "geohash"})
    ds_vn = ds_vn.set_coords("geohash")

    print(ds_vn)

    del ds_vn["location"]
    ds_vn.to_netcdf("stats.nc")

    ddf = ds_vn.to_dask_dataframe(dim_order=["geohash", "time"])
    print(ddf.head())
    print(ddf.dtypes)
    ddf = ddf[ddf.geohash > -1]
    print(ddf.head())
    print("DASK DF:", ddf.shape)

    print("DASK DF 2")

    # ignore precip for now???
    ddf = ddf.dropna(subset=["tavg", "tmin", "tmax", "rad", "rh", "wind"], how="all")
    print("DASK DF 3")

    all_hashes = sorted(list(lookup.keys()))
    print(len(all_hashes))

    # onehundred_each = all_hashes[0::10] + all_hashes[-1:]

    # ddf = ddf.set_index("geohash", divisions=onehundred_each)
    # print(ddf.head())
    # print( "MEMORY TOTAL: ", ddf.memory_usage().sum().compute() / 1024 / 1024 )

    ddf = ddf.set_index("geohash", partition_size="20MB")

    print("DASK DF 4", ddf.npartitions)

    lookup = dask.delayed(lookup)
    partitions = ddf.to_delayed(optimize_graph=True)
    formatted = [
        dask.delayed(writer)(part, i, lookup=lookup)
        for i, part in enumerate(partitions)
    ]

    dask.compute(*formatted)


if __name__ == "__main__":
    client = Client(processes=True)
    print(client)
    main()
