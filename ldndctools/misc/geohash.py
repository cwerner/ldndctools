# source: https://rosettacode.org/wiki/Geohash#Python

# NOTE: This is a very slow and simplistic implementation!
#       ... there are other libs that could be much faster by have C/ C++ code
#       i.e.: https://github.com/hkwi/python-geohash

from typing import Tuple

ch32 = "0123456789bcdefghjkmnpqrstuvwxyz"
bool2ch = {f"{i:05b}": ch for i, ch in enumerate(ch32)}
ch2bool = {v: k for k, v in bool2ch.items()}
ch2int = {k: v for k, v in zip(ch32, range(len(ch32)))}


def bisect(val: float, mn: float, mx: float, bits: int):
    mid = (mn + mx) / 2
    if val < mid:
        bits <<= 1  # push 0
        mx = mid  # range lower half
    else:
        bits = bits << 1 | 1  # push 1
        mn = mid  # range upper half

    return mn, mx, bits


def encoder(lat: float, lng: float, pre: int):
    latmin, latmax = -90, 90
    lngmin, lngmax = -180, 180
    bits = 0
    for i in range(pre * 5):
        if i % 2:
            # odd bit: bisect latitude
            latmin, latmax, bits = bisect(lat, latmin, latmax, bits)
        else:
            # even bit: bisect longitude
            lngmin, lngmax, bits = bisect(lng, lngmin, lngmax, bits)
    # Bits to characters
    b = f"{bits:0{pre * 5}b}"
    geo = (bool2ch[b[i * 5 : (i + 1) * 5]] for i in range(pre))
    return "".join(geo)


def decoder(geo: str):
    minmaxes, latlong = [[-90.0, 90.0], [-180.0, 180.0]], True
    for c in geo:
        for bit in ch2bool[c]:
            minmaxes[latlong][bit != "1"] = sum(minmaxes[latlong]) / 2
            latlong = not latlong
    return minmaxes


def hash2dec(hash_str: str) -> int:
    """convert hash_str to hash_dec"""
    length = len(hash_str)
    bases = [32 ** i for i in range(length)][::-1]

    dec = 0
    for i, d in enumerate(hash_str):
        dec += ch2int[d] * bases[i]
    return dec


def dec2hash(hash_dec: int, pre: int) -> str:
    """convert hash_dec to hash_str"""
    bases = [32 ** i for i in range(pre)][::-1]

    hash_str = ""
    v = hash_dec
    for b in bases:
        a = v // b
        v = v % b
        hash_str += ch32[a]
    return hash_str


def coords2geohash_dec(*, lat: float, lon: float, pre: int = 6) -> int:
    """convert lat, lon coordinate to decimal geohash representation (pre=6)"""
    return hash2dec(encoder(lat, lon, pre))


def geohash_dec2coords(*, geohash_dec: int, pre: int = 6) -> Tuple[float, float]:
    """convert decimal geohash to lat, lon coordinate (we require pre=6)"""
    res = decoder(dec2hash(geohash_dec, pre=pre))
    return round(sum(res[0]) / 2, max(3, pre - 3)), round(
        sum(res[1]) / 2, max(3, pre - 3)
    )
