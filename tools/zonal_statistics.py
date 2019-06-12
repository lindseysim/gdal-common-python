
import math
import numpy
from PIL           import Image, ImageDraw
from raster_utils  import *
from feature_utils import *


def zonalStatistics(feature_data, rasters,
                    bands=None,
                    statistics=("MIN", "MAX", "MEAN", "MEDIAN", "VARIANCE", "STDEV", "PERC90"),
                    ignore_values=None,
                    unique_field=None,
                    name_field=None):
    '''
    Calculate zonal statistics for each feature in a given feature layer on one or more rasters
    :param feature_data: Feature data as filepath, OGR Dataset, or OGR Layer.
    :param rasters: One or list of rasters as filepath or GDAL Dataset.
    :param bands: (Optional) List of bands corresponding to rasters to pull statistics from. Only one band per raster
           and list must match length of rasters exactly (unless only one value supplied, in which case it is applied
           equally to all rasters). If not supplied, the first band will be assumed for all rasters.
    :param statistics: (Optional) List of statistics to pull. If not supplied, all statistics are taken. Currently the
           valid options are: "MIN", "MAX", "MEAN", "MEDIAN", "VARIANCE", "STDEV", "PERC90".
    :param ignore_values: (Optional) Values to ignore when collecting pixels for zonal statistics. As the script by
           itself does not ignore no-data values inherently, it is HIGHLY suggested that at least the raster no-data
           value is specified here. This will be applied to all rasters equally.
    :param unique_field: (Optional) Unique field name in features to identify the corresponding row in the statistics
           table. If not supplied, will attempt to find common unique field names ("OID", "FID", "OBJECTID", etc.) but
           script will fail if no unique field can be ascertained.
    :param name_field: (Optional) An optional field name to include in the outputs.
    :return: Table of results as an array of dictionaries (with keys being column names). Columns will be the
             unique-field, the pixel count, then the statistics requested.
    '''
    if rasters is None:
        raise Exception("No rasters supplied")
    # raster must be list of rasters or single raster
    if not isinstance(rasters, (list, tuple)):
        rasters = [rasters]
    elif len(rasters) == 0:
        raise Exception("No rasters supplied")
    for i in range(len(rasters)):
        raster = rasters[i]
        if raster is None:
            continue
        # if string given, try to open as filepath to a raster
        if isinstance(raster, basestring):
            rasters[i] = getRasterAsGdal(raster)
        else:
            assert isinstance(raster, gdal.Dataset)

    if bands is None:
        # if no bands supplied, assume first band for every raster
        bands = [1] * len(rasters)
    else:
        # bands must be list of bands as number or single band number
        if isinstance(bands, (list, tuple)):
            bands = [bands]
        for band in bands:
            assert isinstance(band, int, long)
        if len(bands) != len(rasters):
            # is just one value, apply to all rasters, otherwise throw error if inconsistent lengths
            if len(bands) == 1:
                bands *= len(rasters)
            else:
                raise Exception("Inconsistent number of rasters and bands given")

    # check if all rasters are alike (if they are we can save some calculations down the road)
    identical_rasters = True
    check_transform = None
    for raster in rasters:
        if raster is None:
            continue
        origin, pixel_size, width, height = getRasterTransform(raster)
        if check_transform is None:
            check_transform = {
                'origin': origin,
                'pixel_size': pixel_size,
                'width': width,
                'height': height
            }
        else:
            if (origin != check_transform['origin'] or pixel_size != check_transform['pixel_size']
                    or width != check_transform['width'] or height != check_transform['height']):
                identical_rasters = False
                break

    # correct ignore value(s)
    if not isinstance(ignore_values, (list, tuple)):
        ignore_values = [ignore_values]
    for val in ignore_values:
        assert isinstance(val, (int, long, float))

    # get feature layer object (flexible in input parameters)
    if isinstance(feature_data, ogr.DataSource):
        # is datasource, get layer
        feature_layer = feature_data.GetLayer()
    elif isinstance(feature_data, ogr.Layer):
        # is already feature layer
        feature_layer = feature_data
    elif isinstance(feature_data, basestring):
        # is string, try to open as filepath
        feature_layer = getFeatureDataset(feature_data).getLayer()
    else:
        raise Exception("Feature dataset is not filepath, OGR Dataset, or OGR Layer")

    # get unique field and type for feature layer
    if unique_field is None:
        unique_field, unique_field_index, unique_field_type = getUniqueField(feature_layer, unique_field)
    else:
        defn = feature_layer.GetLayerDefn()
        f_defn = defn.GetFieldDefn()
        unique_field = f_defn.GetName()
        unique_field_type = f_defn.GetFieldTypeName(f_defn.GetType())
    unique_field_type = unique_field_type.lower()

    # get name field and type
    if name_field:
        name_field, name_field_index, name_field_type = getField(feature_layer, name_field)
        name_field_type = name_field_type.lower()

    # check input statistics
    if statistics is None or len(statistics) == 0:
        raise Exception("No statistics supplied in parameters")
    # also try grabbing stats on empty array to check for invalid stats names
    if len(calculateStatistics([], statistics)) != len(statistics):
        raise Exception("Unrecognized statistics type in parameters, check parameter/spelling")

    count = 0    # loop counter for progress
    table = []    # table (array of dictionaries) for results

    # loop through features (reset iterator since gdal/ogr doesn't)
    feature_layer.SetNextByIndex(0)
    for feature in feature_layer:
        row = {}

        # get unique field value
        if unique_field_type == "real":
            row[unique_field] = feature.GetFieldAsDouble(unique_field_index)
        elif unique_field_type == "integer":
            row[unique_field] = feature.GetFieldAsInteger(unique_field_index)
        elif unique_field_type == "datetime":
            row[unique_field] = feature.GetFieldAsDateTime(unique_field_index)
        else:
            row[unique_field] = feature.GetFieldAsString(unique_field_index)

        # get name field values
        if name_field:
            if name_field_type == "real":
                row[name_field] = feature.GetFieldAsDouble(name_field_index)
            elif name_field_type == "integer":
                row[name_field] = feature.GetFieldAsInteger(name_field_index)
            elif name_field_type == "datetime":
                row[name_field] = feature.GetFieldAsDateTime(name_field_index)
            else:
                row[name_field] = feature.GetFieldAsString(name_field_index)


        # if all rasters have same geotransform, we only need to get the window and polygon as array once so pre-create
        if identical_rasters:
            for raster in rasters:
                if raster is not None:
                    origin, resolution, offset, pixel_size = getFeatureToRasterWindow(raster, feature)
                    poly_array = featureToArray(feature, origin, pixel_size, resolution)
                    break

        # empty list of pixels to be added to
        pixels = []
        # counts per raster
        counts = {"count_total": 0}
        # loop through rasters
        for i in range(len(rasters)):
            pixel_count = 0
            if rasters[i] is not None:
                if identical_rasters:
                    # if identical, use the values already created
                    add_pixels = getPixelsByMaskArray(rasters[i], bands[i], poly_array, offset, resolution, ignore_values)
                else:
                    # if not identical, create new window and feature as array for each raster just in case
                    add_pixels = getPixelsByFeatureMask(rasters[i], bands[i], feature, ignore_values)
                pixel_count = len(add_pixels)
                pixels += add_pixels
            if len(rasters) > 1:
                counts["count_"+str(i+1)] = pixel_count
            counts["count_total"] += pixel_count

        # get count and statistics from list of pixels
        row.update(counts)
        row.update(calculateStatistics(pixels, statistics))

        # append and iterate
        table.append(row)
        count += 1

    return table


def calculateStatistics(pixel_values, options=("MIN", "MAX", "MEAN", "MEDIAN", "VARIANCE", "STDEV", "PERC90")):
    '''
    Calculate statistics on given list of values.
    :param pixel_values: List of numeric values.
    :param options: (Optional) List of statistics to calculate. Default calculates all. The recognized parameters are:
           MIN, MINIMUM - The minimum value
           MAX, MAXIMUM - The maximum value
           MEAN, AVERAGE, AVG - The mean value
           MEDIAN - The median value
           VAR, VARIANCE - The variance
           STDEV - The standard deviation
           PERC90 - The 90th percentile value
    :return: Dictionary of the requested statistics
    '''
    # capitalize options
    options = [stat.upper() for stat in options]
    # check which options are set
    calculate = {
        'min': ("MIN" in options or "MINIMUM" in options),
        'max': ("MAX" in options or "MAXIMUM" in options),
        'mean': ("MEAN" in options or "AVERAGE" in options or "AVG" in options),
        'median': ("MEDIAN" in options),
        'var': ("VAR" in options or "VARIANCE" in options),
        'stdev': ("STDEV" in options),
        'perc90': ("PERC90" in options)
    }
    # create empty stats dictionary to return
    stats = {}
    for key, boolean in calculate.iteritems():
        if boolean:
            stats[key] = 0
    # if empty array, return blank stats dict (but do after creating stats keys)
    if pixel_values is None or len(pixel_values) == 0:
        return stats
    # prepare some variables for loop
    mean = 0
    num_vals = len(pixel_values)
    # various statistics are derived off the mean which is calculated first
    if calculate['mean'] or calculate['stdev'] or calculate['var']:
        for val in pixel_values:
            mean += float(val)/float(num_vals)
    if calculate['mean']:
        stats['mean'] = mean
    # stats that require a secondary loop after mean calculation
    if calculate['stdev'] or calculate['var']:
        variance = 0
        for val in pixel_values:
            variance += (float(val) - mean) ** 2 / float(num_vals)
        if calculate['var']:
            stats['var'] = variance
        if calculate['stdev']:
            stats['stdev'] = variance ** 0.5
    # stats that require a sorted array
    if calculate['min'] or calculate['max'] or calculate['median'] or calculate['perc90']:
        pixel_values.sort()
        if calculate['min']:
            stats['min'] = pixel_values[0]
        if calculate['max']:
            stats['max'] = pixel_values[-1]
        if calculate['median'] and num_vals > 0:
            stats['median'] = pixel_values[int(round(0.5*num_vals))-1]
        if calculate['perc90'] and num_vals > 0:
            stats['perc90'] = pixel_values[int(math.ceil(0.9*num_vals))-1]
    # return stats dictionary
    return stats


def getPixelsByFeatureMask(raster, band, feature, ignore_values=None):
    '''
    Get all pixel-values in raster that are overlapped by the given feature.
    :param raster: The GDAL Dataset to pull pixel values.
    :param band: The band number.
    :param feature: The OGR Feature to define overlap.
    :param ignore_values: (Optional) values to ignore/not-included.
    :return: Array of pixel values.
    '''
    # get overlapping/snapped window to compare feature and raster
    origin, resolution, offset, pixel_size = getFeatureToRasterWindow(raster, feature)
    if origin is None:
        return []
    # rasterize (array-ize?) feature in window
    polyArray = featureToArray(feature, origin, pixel_size, resolution)
    return getPixelsByMaskArray(raster, band, polyArray, offset, resolution, ignore_values)


def getPixelsByMaskArray(raster, band, mask, offset, resolution=None, ignore_values=None):
    '''
    Get all pixel-values in raster using a raster/array mask.
    :param raster: The GDAL Dataset to pull pixel values.
    :param band: The band number.
    :param mask: Shaped NumPy array of the mask as presence (1) or absence (0) values.
    :param offset: The x/y offset of the mask.
    :param resolution: (Optional) The pixel width and height of the mask. If not supplied can just be determined from
           shape of input mask array.
    :param ignore_values: (Optional) values to ignore/not-included.
    :return: Array of pixel values.
    '''
    if raster is None or mask is None or offset is None:
        return []
    if resolution is None:
        resolution = [mask.shape[1], mask.shape[0]]
    # read raster values in window
    pixels = readRaster(raster, band, offset[0], offset[1], resolution[0], resolution[1])
    # empty list of valid pixel values
    values = []
    # loop by lines then pixels, pull raster value if feature presence exists
    for y in range(resolution[1]):
        for x in range(resolution[0]):
            m = mask[y][x]  # numpy stores axes backwards somehow
            if m > 0:
                v = pixels[y][x]  # numpy stores axes backwards somehow
                if ignore_values is None or v not in ignore_values:
                    values.append(v)
    return values


def getFeatureToRasterWindow(raster, feature):
    '''
    Given a feature which overlaps a raster, find the geotransformation for the pixel window of the overlap, snapping to
    the raster grid and pixel size.
    :param raster: The GDAL Dataset
    :param feature: The OGR Feature
    :return: Tuple of origin (as array), resolution (as array), x/y-offsets (as tuple), pixel width, and pixel height.
    '''
    # get raster information
    origin, pixel_size, width, height = getRasterTransform(raster)
    raster_band = raster.GetRasterBand(1)
    # get feature information
    xmin, xmax, ymin, ymax = getFeatureExtent(feature)
    # snap x-origin to raster grid and crop to minimum corner
    if xmin < origin[0]:
        xmin = origin[0]
    else:
        xmin -= (xmin - origin[0]) % pixel_size[0]
    # calculate x-offset
    xoffset = int((xmin - origin[0]) / pixel_size[0])
    # since origin is often at top with a negative y-pixel-size, getting y-origin and y-offset is a little more complex
    if pixel_size[1] < 0:
        if ymax > origin[1]:
            ymax = origin[1]
        else:
            ymax -= (origin[1] - ymax) % pixel_size[1]
        yoffset = int((ymax - origin[1]) / pixel_size[1])
    else:
        if ymax < origin[1]:
            ymin = origin[1]
        else:
            ymin -= (ymin - origin[1]) % pixel_size[1]
        yoffset = int((ymin - origin[1]) / pixel_size[1])
    # get resolution, i.e. extent of window in x,y pixels
    resolution = [
        int((xmax - xmin)/pixel_size[0]),
        int((ymax - ymin)/pixel_size[1])
    ]
    # since origin is at top-left usually, have to change sign on y-resolution
    if pixel_size[1] < 0:
        resolution[1] = -resolution[1]
    # outside of extent return empty array
    if xoffset > raster_band.XSize or yoffset > raster_band.YSize:
        return None, None, None, None
    # adjust extent to fit within raster
    if xoffset + resolution[0] > raster_band.XSize:
        resolution[0] = raster_band.XSize - xoffset
    if yoffset + resolution[1] > raster_band.YSize:
        resolution[1] = raster_band.YSize - yoffset
    # flat resolution after adjusting, return empty array
    if resolution[0] <= 0 or resolution[1] <= 0:
        return None, None, None, None
    # At this point we have our adjusted, cropped, and aligned window
    return (
        [xmin, ymax if pixel_size[1] < 0 else ymin],    # origin
        resolution,                                        # resolution/extent
        [xoffset, yoffset],                                # offset in raster
        pixel_size                                        # pixel size
    )


def featureToArray(feature, origin, pixel_size, resolution):
    '''
    Convert a feature into an array (basically raster) of presence/absence (1,0) values.
    :param feature: The OGR Feature.
    :param origin: Coordinates for the raster/array origin (as array).
    :param pixel_size: The x and y pixel sizes (as array).
    :param resolution: The pixel width and height (as array).
    :return: NumPy array of 0,1 values in shape specified by resolution.
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
                    calcPixelCoordinate(
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
