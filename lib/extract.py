from .. import features, fields
from .. import rasters as rasterutils
from ._getlayer import get as _getLayer
from .conversion import featureToArray


def extractFeatures(input_datasource, validation_func, output_path, overwrite=False):
    '''
    Extract features from a datasource using a callback function.
    :param input_datasource:  (ogr.DataSource|ogr.Layer|str) The feature datasource to extract from, provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param validation_func: (callback) The validation function, which returns True if feature is to be extracted, or
           False if filtered out. Provided ogr.Feature as only parameter.
    :param output_path: (str) The output path to save the extracted features to.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return:
    '''
    input_layer, ds  = _getLayer(input_datasource, allow_path=True)
    input_datasource = input_datasource if not ds else ds
    output_ds        = features.copyFeatureDataSourceAsEmpty(input_datasource, output_path, overwrite)
    output_layer     = output_ds.GetLayer()

    input_layer.SetNextByIndex(0)
    feat = input_layer.GetNextFeature()
    while feat:
        if validation_func(feat):
            output_layer.CreateFeature(feat)
        feat = input_layer.GetNextFeature()
    input_layer.SetNextByIndex(0)

    if ds:
        ds.Release()
        del input_layer, ds, input_datasource

    return output_ds


def selectFeatures(input_datasource, on_fields, validation_func, output_path, overwrite=False):
    '''
    Extract features from a datasource using a callback function. Difference from extractFeatures() is that field values
    are read and provided to callback function.
    :param input_datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource to extract from, provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param on_fields: (common.Field[]|ogr.FieldDefn[]|str[]) The fields to read for each feature and provide to the
           callback/validation function. May be provided as list containing instances of Field, ogr.FieldDefn, or field
           names.
    :param validation_func: (callback) The validation function, which returns True if feature is to be extracted, or
           False if filtered out. Provided an array of values corresponding to the fields provided in `on_fields` for
           the feature.
    :param output_path: (str) The output path to save the extracted features to.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return:
    '''
    input_layer, ds  = _getLayer(input_datasource, allow_path=True)
    input_datasource = input_datasource if not ds else ds
    output_ds        = features.copyFeatureDataSourceAsEmpty(input_datasource, output_path, overwrite)
    output_layer     = output_ds.GetLayer()
    copy_fields      = [fields.get(input_layer, f) for f in on_fields]

    input_layer.SetNextByIndex(0)
    feat = input_layer.GetNextFeature()
    while feat:
        values = [fields.value(feat, f) for f in copy_fields]
        if validation_func(values):
            output_layer.CreateFeature(feat)
        feat = input_layer.GetNextFeature()
    input_layer.SetNextByIndex(0)

    if ds:
        ds.Release()
        del input_layer, ds, input_datasource

    return output_ds


def getPixelsByFeatureMask(raster, band, feature, ignore_values=None):
    '''
    Get all pixel-values in raster that are overlapped by the given feature.
    :param raster: (gdal.Dataset) The GDAL Dataset to pull pixel values.
    :param band: (int) The band number, starting at 1.
    :param feature: (ogr.Feature) The OGR Feature to define overlap.
    :param [ignore_values]: (float[]) Values to ignore/not-included (can also be callback function provided pixel value
           as only parameter, return True to ignore).
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
    :param raster: (gdal.Dataset) The GDAL Dataset to pull pixel values.
    :param band: (int) The band number, starting at 1.
    :param mask: (numpy.Array) Shaped NumPy array of the mask as presence (1) or absence (0) values.
    :param offset: (int[]) The x/y offset of the mask.
    :param [resolution]: (int[]) The pixel width and height of the mask. If not supplied can just be determined from
           shape of input mask array.
    :param [ignore_values]: (float[]) Values to ignore/not-included (can also be callback function provided pixel value
           as only parameter, return True to ignore).
    :return: (float[]) Pixel values as flat list.
    '''
    if raster is None or mask is None or offset is None:
        return []
    if resolution is None:
        resolution = [mask.shape[1], mask.shape[0]]
    # read raster values in window
    pixels = rasterutils.readRaster(raster, band, offset[0], offset[1], resolution[0], resolution[1])
    # empty list of valid pixel values
    values = []
    # loop by lines then pixels, pull raster value if feature presence exists
    for y in range(resolution[1]):
        for x in range(resolution[0]):
            m = mask[y][x]  # numpy stores axes backwards somehow
            if m > 0:
                v = pixels[y][x]  # numpy stores axes backwards somehow
                if ignore_values:
                    if callable(ignore_values):
                        if not ignore_values(v):
                            values.append(v)
                    elif v not in ignore_values:
                        values.append(v)
    return values


def getFeatureToRasterWindow(raster, feature):
    '''
    Given a feature which overlaps a raster, find the geotransformation for the pixel window of the overlap, snapping to
    the raster grid and pixel size.
    :param raster: (gdal.Dataset) The GDAL Dataset
    :param feature: (ogr.Feature) The OGR Feature
    :return: Tuple of origin (as float[]), resolution (as int[]), x/y-offsets (as int[]), and pixel sizes (as float[])
             corresponding to window on raster that overlaps the feature provided.
    '''
    # get raster information
    origin, pixel_size, extent = rasterutils.getRasterTransform(raster)
    width = extent[0]
    height = extent[1]
    raster_band = raster.GetRasterBand(1)
    # get feature information
    xmin, xmax, ymin, ymax = features.getFeatureExtent(feature)
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
        [xmin, ymax if pixel_size[1] < 0 else ymin],  # origin
        resolution,                                   # resolution/extent
        [xoffset, yoffset],                           # offset in raster
        pixel_size                                    # pixel size
    )
