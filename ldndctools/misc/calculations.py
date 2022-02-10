import math
from typing import Tuple

from ldndctools.misc.errors import ParameterMissingError
from ldndctools.misc.types import LayerData


# currently not used
def calc_litter_properties(
    litter_mass: float, litter_name: str
) -> Tuple[float, float, float]:  # mass in t C ha-1
    """calculate litter height based on litter type and mass"""
    if litter_name == "MULL":
        density = 0.2
        accumulation_factor = 1.5
    elif litter_name == "MODER":
        density = 0.25
        accumulation_factor = 2.5
    else:
        density = 0.3
        accumulation_factor = 3.5

    # explanation:
    #   (tCha-1) > x2 > tBMha-1 > x0.1 > kgBMm-2 > x0.1 > gBMcm-2 >
    #   /density > height_cm > *10 > height_mm
    # littermass (t C ha-1) * 2 (BM conv) * 0.1 * 0.1 / density * 10
    depth = ((litter_mass * accumulation_factor * 2 * 0.1 * 0.1) / density) * 10.0
    n_layers = math.floor(depth / 20.0)
    layer_height = depth
    if n_layers > 0:
        layer_height = 20.0 + ((depth % 20.0) / n_layers)
    return (density, depth, layer_height)


# currently not used
# TODO: remove?
def calcHeight(TK, N):
    if TK == -9999:
        TKmm = -9999
    else:
        TKmm = TK * 10  # change the unit from cm to mm

    if TKmm > -9999:
        numberOfLayers = math.floor(TKmm / N)
        if numberOfLayers != 0:
            layerHeight = N + ((TKmm % N) / numberOfLayers)
        else:
            layerHeight = TKmm
    else:
        layerHeight = -9999
    return (TKmm, layerHeight)


def calc_hydraulic_properties(ld: LayerData) -> LayerData:
    """Calc hydraulic properties based on et al. (1996)

    shape parameters: Woesten et al. (1999) Geoderma

    OM (% organic matter)
    D (bulk density)
    topsoil 1, subsoil 0
    C, S, (clay, silt in %)

    formula:
    θ_s = 0.7919 + 0.001691 * C - 0.29619 * D - 0.000001491 * S*S + \
          0.0000821 * OM * OM + 0.02427 * C**-1 + 0.01113 * S**-1 + \
          0.01472 * math.ln( S ) - 0.0000733 * OM * C - 0.000619 * D * C - \
          0.001183 * D * OM - 0.0001664 * topsoil * S

    ad-hoc AG Boden

    Sand, Clay [%], BD [g cm-3], Corg [%]
    """

    if None in [ld.corg, ld.clay, ld.sand, ld.bd]:
        raise ParameterMissingError("Required: corg, clay, sand, bd")

    # convert units
    corg = ld.corg * 100
    clay = ld.clay * 100
    sand = ld.sand * 100
    bd = ld.bd

    theta_r = 0.015 + 0.005 * clay + 0.014 * corg
    theta_s = 0.81 - 0.283 * bd + 0.001 * clay

    log_n = 0.053 - 0.009 * sand - 0.013 * clay + 0.00015 * sand ** 2
    log_alpha = -2.486 + 0.025 * sand - 0.351 * corg - 2.617 * bd - 0.023 * clay

    alpha = math.e ** log_alpha
    vgn = math.e ** log_n
    vgm = 1.0  # (1.0 - (1.0/ vGn)) off as we do not use texture classes but real frac

    field_capacity = theta_r + (theta_s - theta_r) / math.pow(
        (1.0 + math.pow(alpha * 100.0, vgn)), vgm
    )
    wilting_point = theta_r + (theta_s - theta_r) / math.pow(
        (1.0 + math.pow(alpha * 15800.0, vgn)), vgm
    )

    # TODO: check this more systematically
    #
    # Which combo of soil parameters is valid and should be corrected if
    # wcmin/ wcmax calc is bad, and which should be blocked and raised

    try:
        if field_capacity < wilting_point:
            raise ValueError("Field capacity < wilting point!")

    except ValueError:
        print(
            "WARNING: Field capacity < wilting point! Fixing with: wcmin = wcmax - 10"
        )
        wilting_point = field_capacity - 0.01

    ld.wcmax = field_capacity * 1000
    ld.wcmin = wilting_point * 1000

    return ld
