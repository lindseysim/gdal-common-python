import numpy
from PIL import Image, ImageDraw
from ._getlayer import get as _getLayer
from .. import rasters as rasterutils


def featuresToGeoJson(datasource):
    '''
    Convert a feature datasource to a GeoJSON string.
    :param datasource: (ogr.DataSource) The feature datasource to convert.
    :return: (str) The GeoJSON string.
    '''
    feat_layer, ds = _getLayer(datasource, allow_path=True)
    geojson = (
        '{\n' +
        '  "type": "FeatureCollection", \n' +
        '  "features": [\n'
    )
    first = True
    for feature in feat_layer:
        if first:
            first = False
        else:
            geojson += ",\n"
        geojson += "    " + feature.ExportToJson()
    geojson += "\n  ]\n}"
    if ds:
        ds.Release()
        del feat_layer, ds
    return geojson


def featureToArray(feature, origin, pixel_size, resolution):
    '''
    Convert a feature into an array (basically raster) of presence/absence (1,0) values.
    :param feature: (ogr.Feature) The OGR Feature.
    :param origin: (float[]) Coordinates for the raster/array origin (as array).
    :param pixel_size: (float[]) The x and y pixel sizes (as array).
    :param resolution: (int[]) The pixel width and height (as array).
    :return: (numpy.Array) NumPy array of 0,1 values in shape specified by resolution.
    '''
    if feature is None or origin is None or pixel_size is None or resolution is None:
        return []
    # create image
    rasterPoly = Image.new("L", (resolution[0], resolution[1]), 0)
    rasterize = ImageDraw.Draw(rasterPoly)
    # get parent geometry
    geom = feature.GetGeometryRef()
    geom_type = geom.GetGeometryName()
    # add polygons from either polygon or multipolygon type
    polygons = []
    if geom_type == "POLYGON":
        polygons.append(geom)
    elif geom_type == "MULTIPOLYGON":
        for p in range(geom.GetGeometryCount()):
            polygons.append(geom.GetGeometryRef(p))
    else:
        raise Exception("Unsupported geometry type for mask: " + geom_type)
    # loop through polygons
    for poly in polygons:
        outer = True
        # loop through ring
        for r in range(poly.GetGeometryCount()):
            ring = poly.GetGeometryRef(r)
            if ring.GetGeometryName() != "LINEARRING":
                raise Exception("LINEARRING geometry expected in POLYGON, " + ring.GetGeometryName() + " geometry found")
            pixels = []
            # create pixels from ring
            for p in range(ring.GetPointCount()):
                pixels.append(
                    rasterutils.calcPixelCoordinate(
                        [ring.GetX(p), ring.GetY(p)],
                        origin,
                        pixel_size
                    )
                )
            # draw ring as polygon (if inner-ring, erase)
            rasterize.polygon(pixels, 1 if outer else 0)
            outer = False
    # convert image to numpy array
    polyArray = numpy.array(list(rasterPoly.getdata()))
    polyArray.shape = resolution[1], resolution[0]
    # return array
    return polyArray