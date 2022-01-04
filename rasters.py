from osgeo import gdal, osr
from osgeo.gdalconst import *



GEOTIFF_DRIVER_NAME        = "GTiff"
ERDAS_IMAGINE_DRIVER_NAME  = "HFA"
GENERIC_BINARY_DRIVER_NAME = "GENBIN"
ESRI_GRID_DRIVER_NAME      = "AAIGrid"


def guessRasterDriver(path):
    '''
    Guess raster driver by filename. Limited support, still needs fleshing out. Throws exception if cannot be
    determined.
    :param path: (str) Filepath to raster.
    :return: (str) GDAL raster driver name.
    '''
    path = path.lower()
    if path.endswith(".tif"):
        return GEOTIFF_DRIVER_NAME
    elif path.endswith(".img"):
        return ERDAS_IMAGINE_DRIVER_NAME
    elif path.endswith(".hdf"):
        return GENERIC_BINARY_DRIVER_NAME
    elif path.endswith(".asc"):
        return ESRI_GRID_DRIVER_NAME
    else:
        raise Exception("Raster file extension not recognized, create raster driver manually.")


def getRasterDriver(path):
    '''
    Get the raster driver by filename. Limited support, still needs fleshing out. Throws exception if cannot be
    determined.
    :param path: (str) Filepath to raster.
    :return: (gdal.Driver)
    '''
    return gdal.GetDriverByName(guessRasterDriver(path))


def getRasterAsGdal(rasterpath):
    '''
    Get raster dataset as gdal.Dataset instance.
    :param rasterpath: (str) The filepath to the raster.
    :return: (gdal.Dataset)
    '''
    dataset = gdal.Open(rasterpath, GA_ReadOnly)
    return dataset


def getRasterSpatialReference(dataset):
    '''
    Get the spatial reference of a raster dataset.
    :param dataset: (gdal.Dataset) The raster dataset.
    :return: (ogr.SpatialReference)
    '''
    if dataset is None:
        return None
    prj = dataset.GetProjection()
    return osr.SpatialReference(wkt=prj)


def getRasterTransform(dataset):
    '''
    Get the raster transform of a raster dataset.
    :param dataset: (gdal.Dataset) The raster dataset.
    :return: A tuple of three lists. Each list is a pair for x/y origin, pixel size, and extent, respectively.
    '''
    if dataset is None:
        return None
    geo_transform = dataset.GetGeoTransform()
    if geo_transform is None:
        return None
    return (
        [geo_transform[0], geo_transform[3]],       # origin (x,y)
        [geo_transform[1], geo_transform[5]],       # pixel size (x,y)
        [dataset.RasterXSize, dataset.RasterYSize]  # extent (width, height)
    )


def calcPixelCoordinate(coordinate, origin=None, pixel_size=None, dataset=None):
    '''
    Calculated the pixel coordinates from a given set of coordinates. Must be provided either the raster dataset or both
    the origin and pixel size for a dataset.
    :param coordinate: (float[]) The real coordinates (in same SRS as raster).
    :param [origin]: (float[]) Pixel origin.
    :param [pixel_size]: (float[]) Pixel sizes.
    :param [dataset]: (gdal.Dataset) The raster dataset.
    :return: (int[]) The pixel coordinates in x/y-distance in pixels from origin.
    '''
    if not origin or not pixel_size:
        origin, pixel_size, extent = getRasterTransform(dataset)
    return (
        int((coordinate[0] - origin[0]) / pixel_size[0]),
        int((coordinate[1] - origin[1]) / pixel_size[1])
    )


def createRasterTransform(origin, pixel_size):
    '''
    Create raster transform parameters.
    :param origin: (float[]) Pixel origin.
    :param pixel_size: (float[]) Pixel sizes.
    :return: (float[]) The raster transform parameters (origin-x, pixel-size-x, 0, origin-y, 0, pixel-size-y).
    '''
    return [origin[0], pixel_size[0], 0, origin[1], 0, pixel_size[1]]


def getNoDataValue(dataset, band):
    '''
    Get the no data value for a raster band.
    :param dataset: (gdal.Dataset) The raster dataset.
    :param band: (int) The band number (starting at 1).
    :return:
    '''
    return dataset.GetRasterBand(band).GetNoDataValue()


def readRaster(dataset, band, offset_x, offset_y, length_x=1, length_y=1):
    '''
    Read and return raster values.
    :param dataset: (gdal.Dataset) The raster dataset.
    :param band: (int) The band number (starting at 1).
    :param offset_x: X-offset to start reading, in pixels.
    :param offset_y: Y-offset to start reading, in pixels.
    :param length_x: The window width, in number of pixels, to read.
    :param length_y: The window height, in number of pixels, to read.
    :return: (numpy.Array) Two-dimension array of raster values corresponding to window size. Note array is returned as
             arr[y][x] to conform to NumPy conventions.
    '''
    read_band = dataset.GetRasterBand(band)
    width = read_band.XSize
    height = read_band.YSize
    if offset_x > width or offset_x < 0:
        raise Exception("Offset (x) is greater than band width or negative")
    if offset_y > height or offset_y < 0:
        raise Exception("Offset (y) is greater than band height or negative")
    if length_x == 0:
        length_x = width - offset_x
    elif length_x < 0:
        raise Exception("Read length (x) cannot be negative")
    elif offset_x + length_x > width:
        raise Exception("Offset plus length (x) is greater than band width")
    if length_y == 0:
        length_y = height - offset_y
    elif length_y < 0:
        raise Exception("Read length (y) cannot be negative")
    elif offset_y + length_y > height:
        raise Exception("Offset plus length (y) is greater than band height")
    return read_band.ReadAsArray(offset_x, offset_y, length_x, length_y)
