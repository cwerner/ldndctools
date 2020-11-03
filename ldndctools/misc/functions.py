import math
import xml.dom.minidom as MD
import xml.etree.cElementTree as ET


def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
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


def calcLitter(litterMass, litname):  # mass in t C ha-1
    if litname == "MULL":
        density = 0.2
        accumulationFactor = 1.5
    elif litname == "MODER":
        density = 0.25
        accumulationFactor = 2.5
    else:
        density = 0.3
        accumulationFactor = 3.5

    # explanation:
    #   (tCha-1) > x2 > tBMha-1 > x0.1 > kgBMm-2 > x0.1 > gBMcm-2 >
    #   /density > height_cm > *10 > height_mm
    # littermass (t C ha-1) * 2 (BM conv) * 0.1 * 0.1 / density * 10
    depth = ((litterMass * accumulationFactor * 2 * 0.1 * 0.1) / density) * 10.0
    numberOfLayers = math.floor(depth / 20.0)
    layerHeight = depth
    if numberOfLayers != 0:
        layerHeight = 20.0 + ((depth % 20.0) / numberOfLayers)
    return (density, depth, layerHeight)


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
