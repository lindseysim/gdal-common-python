import math
from osgeo import gdal
from ..Field import Field
from ._getlayer import get as _get_layer
from .. import fields
from .. import rasters as rasterutils
from . import conversion
from . import extract


def statistics(feature_data, rasters, bands=None,
               statistics=("MIN", "MAX", "MEAN", "MEDIAN", "VARIANCE", "STDEV", "PERC90"),
               ignore_values=None,
               unique_field=None,
               name_field=None):
    '''
    Calculate zonal statistics for each feature in a given feature layer on one or more rasters
    :param feature_data: (str) Feature data as filepath, OGR Dataset, or OGR Layer.
    :param rasters: (str[]|gdal.Dataset[]) One or list of rasters as filepath or GDAL Dataset.
    :param [bands]: (int[]) List of bands corresponding to rasters to pull statistics from. Only one band per raster and
           list must match length of rasters exactly (unless only one value supplied, in which case it is applied
           equally to all rasters). If not supplied, the first band will be assumed for all rasters.
    :param [statistics]: (str[]) List of statistics to pull. If not supplied, all statistics are taken. Currently the
           valid options are: "MIN", "MAX", "MEAN", "MEDIAN", "VARIANCE", "STDEV", "PERC90".
    :param [ignore_values]: (int[]|float[]|callback) Values to ignore when collecting pixels for zonal statistics. Can
           also be callback function, return True to ignore) As the script by itself does not ignore no-data values
           inherently, it is HIGHLY suggested that at least the raster no-data value is specified here. This will be
           applied to all rasters equally.
    :param [unique_field]: (str) Unique field name in features to identify the corresponding row in the statistics
           table. If not supplied, will attempt to find common unique field names ("OID", "FID", "OBJECTID", etc.) but
           script will fail if no unique field can be ascertained.
    :param [name_field]: (str) An optional field name to include in the outputs.
    :return: (dict[]) Table of results as an array of dictionaries (with keys being column names). Columns will be the
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
        rast = rasters[i]
        if rast is None:
            continue
        # if string given, try to open as filepath to a raster
        if isinstance(rast, str):
            rasters[i] = rasterutils.get_dataset(rast)
        else:
            assert isinstance(rast, gdal.Dataset)

    if bands is None:
        # if no bands supplied, assume first band for every raster
        bands = [1] * len(rasters)
    else:
        # bands must be list of bands as number or single band number
        if isinstance(bands, (list, tuple)):
            bands = [bands]
        for band in bands:
            assert isinstance(band, int)
        if len(bands) != len(rasters):
            # is just one value, apply to all rasters, otherwise throw error if inconsistent lengths
            if len(bands) == 1:
                bands *= len(rasters)
            else:
                raise Exception("Inconsistent number of rasters and bands given")

    # check if all rasters are alike (if they are we can save some calculations down the road)
    identical_rasters = True
    check_transform = None
    for rast in rasters:
        if rast is None:
            continue
        origin, pixel_size, extent = rasterutils.get_transform(rast)
        width = extent[0]
        height = extent[1]
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
    if ignore_values or ignore_values == 0:
        if not callable(ignore_values):
            if not isinstance(ignore_values, (list, tuple)):
                ignore_values = [ignore_values]
            for val in ignore_values:
                assert isinstance(val, (int, float))

    # get feature layer object
    feature_layer, feature_data = _get_layer(feature_data)

    # get unique field and type for feature layer
    if unique_field is None:
        unique_field = Field(True)
    else:
        unique_field = fields.get(feature_layer, unique_field)

    # get name field and type
    if name_field:
        name_field = fields.get(feature_layer, name_field)

    # check input statistics
    if statistics is None or len(statistics) == 0:
        raise Exception("No statistics supplied in parameters")
    # also try grabbing stats on empty array to check for invalid stats names
    if len(_stats([], statistics)) != len(statistics):
        raise Exception("Unrecognized statistics type in parameters, check parameter/spelling")

    count = 0    # loop counter for progress
    table = []    # table (array of dictionaries) for results

    # loop through features (reset iterator since gdal/ogr doesn't)
    feature_layer.SetNextByIndex(0)
    for feature in feature_layer:
        row = {}
        row[unique_field] = fields.value(feature, unique_field)
        if name_field:
            row[name_field] = fields.value(feature, name_field)

        # if all rasters have same geotransform, we only need to get the window and polygon as array once so 
        # pre-create
        poly_array = offset = resolution = None
        if identical_rasters:
            for raster in rasters:
                if raster is not None:
                    origin, resolution, offset, pixel_size = extract.feature_to_raster_window(raster, feature)
                    poly_array = conversion.feature.to_array(feature, origin, pixel_size, resolution)
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
                    add_pixels = extract.pixels_by_mask_array(rasters[i], bands[i], poly_array, offset, resolution, ignore_values)
                else:
                    # if not identical, create new window and feature as array for each raster just in case
                    add_pixels = extract.pixels_by_feature_mask(rasters[i], bands[i], feature, ignore_values)
                pixel_count = len(add_pixels)
                pixels += add_pixels
            if len(rasters) > 1:
                counts["count_"+str(i+1)] = pixel_count
            counts["count_total"] += pixel_count

        # get count and statistics from list of pixels
        row.update(counts)
        row.update(_stats(pixels, statistics))

        # append and iterate
        table.append(row)
        count += 1

    if feature_data:
        feature_data.Release()
        del feature_data

    return table


def _stats(pixel_values, options=("MIN", "MAX", "MEAN", "MEDIAN", "VARIANCE", "STDEV", "PERC90")):
    '''
    Calculate statistics on given list of values.
    :param pixel_values: (int[]|float[]) Flat list of numeric values.
    :param [options]: (str[]) List of statistics to calculate. Default calculates all. The recognized parameters are:
           MIN, MINIMUM - The minimum value
           MAX, MAXIMUM - The maximum value
           MEAN, AVERAGE, AVG - The mean value
           MEDIAN - The median value
           VAR, VARIANCE - The variance
           STDEV - The standard deviation
           PERC90 - The 90th percentile value
    :return: (dict) Dictionary of the requested statistics
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
    for key, boolean in calculate.items():
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
