"""assorted helper functions that currently do not have a dedicate place (yet)"""
from functools import wraps
import netCDF4
import xarray as xr
import boto3
import os


# from: https://stackoverflow.com/a/54487188/5300574
def mutually_exclusive(keyword, *keywords):
    """decorator for mutually exclusive kwargs"""
    keywords = (keyword,) + keywords

    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if sum(k in keywords for k in kwargs) > 1:
                raise TypeError(
                    "You must specify exactly one of {}".format(", ".join(keywords))
                )
            return func(*args, **kwargs)

        return inner

    return wrapper


# hack to convert xarray to in-memory bytes
def dataset_to_bytes(ds: xr.Dataset, name: str = "my-dataset") -> bytes:
    """Converts dataset to bytes."""

    nc4_ds = netCDF4.Dataset(name, mode="w", diskless=True, memory=ds.nbytes)
    nc4_store = xr.backends.NetCDF4DataStore(nc4_ds)
    ds.dump_to_store(nc4_store)
    res_mem = nc4_ds.close()
    res_bytes = res_mem.tobytes()
    return res_bytes


# push results to s3 bucket and provide download link
def get_s3_link(
    buffer: bytes,
    filename: str,
    content_type: str,
    bucket_name: str,
    endpoint_url: str = "https://s3.imk-ifu.kit.edu:8082",
) -> str:
    session = boto3.Session(profile_name="ifu-s3")

    client = session.client("s3", endpoint_url=endpoint_url)
    client.put_object(
        Body=buffer,
        Bucket=bucket_name,
        ContentType=content_type,
        ContentDisposition=f"attachment;filename={os.path.basename(filename)}",
        Key=filename,
    )

    # NOTE: currently not available for NetApp
    # download_url = client.presigned_get_object(
    #     bucket_name, filename)
    download_url = f"{endpoint_url}/{bucket_name}/{filename}"
    return download_url
