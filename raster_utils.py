import gdal
from gdal import osr
from gdalconst import *



GEOTIFF_DRIVER_NAME        = "GTiff"
ERDAS_IMAGINE_DRIVER_NAME  = "HFA"
GENERIC_BINARY_DRIVER_NAME = "GENBIN"
ESRI_GRID_DRIVER_NAME      = "AAIGrid"


def guessRasterDriver(path):
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


def getRasterDriver(path, driver_name=None):
    return gdal.GetDriverByName(guessRasterDriver(path))


def getRasterAsGdal(rasterpath):
    dataset = gdal.Open(rasterpath, GA_ReadOnly)
    return dataset


def getRasterSpatialReference(dataset):
    if dataset is None:
        return None
    prj = dataset.GetProjection()
    return osr.SpatialReference(wkt=prj)


def getRasterTransform(dataset):
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
    if not origin or not pixel_size:
        origin, pixel_size, extent = getRasterTransform(dataset)
    return (
        int((coordinate[0] - origin[0]) / pixel_size[0]),
        int((coordinate[1] - origin[1]) / pixel_size[1])
    )


def createRasterTransform(origin, pixel_size):
    return [origin[0], pixel_size[0], 0, origin[1], 0, pixel_size[1]]


def getNoDataValue(dataset, band):
    return dataset.GetRasterBand(band).GetNoDataValue()


def readRaster(dataset, band, offset_x, offset_y, length_x=1, length_y=1):
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
