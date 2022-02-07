from importlib import resources

import intake
import pytest

from ldndctools.io.xmlwriter import SiteXmlWriter
from ldndctools.misc.types import RES


@pytest.fixture
def site_xml_writer_lr():
    """return sitexmlwriter for lr data"""
    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    soil = catalog.soil(res=RES.LR.name).read()

    return SiteXmlWriter(soil, res=RES.LR)


@pytest.fixture
def site_xml_writer_hr():
    """return sitexmlwriter for hr data"""
    with resources.path("data", "catalog.yml") as cat:
        catalog = intake.open_catalog(str(cat))

    soil = catalog.soil(res=RES.HR.name).read()

    return SiteXmlWriter(soil, res=RES.HR)


def test_sitexml_lowres_number_of_sites(site_xml_writer_lr):
    assert site_xml_writer_lr.number_of_sites == 60700


def test_sitexml_highres_number_of_sites(site_xml_writer_hr):
    assert site_xml_writer_hr.number_of_sites == 2207986


# def test_sitexml_lowres_number_of_sites(site_xml_writer):