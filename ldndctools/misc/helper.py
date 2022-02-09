"""assorted helper functions that currently do not have a dedicate place (yet)"""
import os
from functools import wraps

import boto3
import netCDF4
import xarray as xr
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


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
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    client = session.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        endpoint_url=endpoint_url,
    )

    client.put_object(
        Body=buffer,
        Bucket=bucket_name,
        ContentType=content_type,
        ContentDisposition=f"attachment;filename={os.path.basename(filename)}",
        Key=filename,
    )

    download_url = client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": filename}, ExpiresIn=300
    )

    return download_url
