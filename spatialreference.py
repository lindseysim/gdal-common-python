from osgeo import osr


EPSG = {
    "NAD83": 4269,
    "WGS84": 4326,
    "Web Mercator": 3857,
    "California Albers (NAD83)": 3310
}


def epsg(epsg):
    return from_epsg(epsg)


def from_epsg(epsg):
    '''
    Get osr.SpatialReference instance from EPSG number.
    :param epsg: (int) EPSG number
    :return: (osr.SpatialReference)
    '''
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    return srs
