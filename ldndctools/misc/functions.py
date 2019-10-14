import math
import xml.etree.cElementTree as ET
import xml.dom.minidom as MD


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = MD.parseString(rough_string)
    str1 = reparsed.toprettyxml(indent="  ")
    str2 = []
    ss = str1.split("\n")
    for s in ss:
        x = "".join(s.split())
        if x != "":
            str2.append(s)
    return "\n".join(str2) + "\n"


def calcHydaulicProperties(D):
    """ Calc hydraulic properties based on et al. (1996) """
    # shape parameters Woesten et al. (1999) Geoderma
    #
    # OM      (% organic matter)
    # D       (bulk denisty)
    # topsoil 1, subsoil 0
    # C, S,   (clay, silt in %)
    #
    # ThetaS = 0.7919 + 0.001691 * C - 0.29619 * D - 0.000001491 * S*S + 0.0000821 * OM * OM + 0.02427 * C**-1 + 0.01113 * S**-1 + \
    #         0.01472 * math.ln( S ) - 0.0000733 * OM * C - 0.000619 * D * C - 0.001183 * D * OM - 0.0001664 * topsoil * S

    # ad-hoc AG Boden
    #
    # Sand, Clay [%], BD [g cm-3], corg [%]

    corg = D["corg"] * 100
    clay = D["clay"] * 100
    sand = D["sand"] * 100
    bd = float(D["bd"])

    ThetaR = 0.015 + 0.005 * clay + 0.014 * corg
    ThetaS = 0.81 - 0.283 * bd + 0.001 * clay

    logAlpha = -2.486 + 0.025 * sand - 0.351 * corg - 2.617 * bd - 0.023 * clay
    logN = 0.053 - 0.009 * sand - 0.013 * clay + 0.00015 * sand ** 2

    try:
        ALPHA = math.e ** logAlpha
    except:
        print(D)
    vGn = math.e ** logN
    vGm = 1.0  # (1.0 - (1.0/ vGn)) disabled as we do not use texture classes but real fractions

    FLDcap = ThetaR + (ThetaS - ThetaR) / math.pow(
        (1.0 + math.pow(ALPHA * 100.0, vGn)), vGm
    )
    WILTpt = ThetaR + (ThetaS - ThetaR) / math.pow(
        (1.0 + math.pow(ALPHA * 15800.0, vGn)), vGm
    )
    return FLDcap * 1000, WILTpt * 1000
