import osr

EPSG = {
    "NAD83": 4269,
    "WGS84": 4326,
    "Web Mercator": 3857,
    "California Albers (NAD83)": 3310
}

def getSpatialRefFromEPSG(epsg):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    return srs
