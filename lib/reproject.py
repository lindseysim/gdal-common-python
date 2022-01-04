import os
import math
from osgeo import gdal, ogr, osr
from ._getlayer import get as _getLayer
from .. import features, rasters


def reprojectFeatures(input_datasource, output_path, to_srs, overwrite=False):
    '''
    Reproject a feature datasource.
    :param input_datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource to reprojected, provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param output_path: (str) The output path to write the reprojected feature datasource.
    :param to_srs: (osr.SpatialReference) The spatial reference to reproject to.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return:
    '''
    input_layer, ds  = _getLayer(input_datasource, allow_path=True)
    input_datasource = input_datasource if not ds else input_datasource
    layer_defn       = input_layer.GetLayerDefn()

    from_srs  = input_layer.GetSpatialRef()
    transform = osr.CoordinateTransformation(from_srs, to_srs)

    reproj_ds    = features.copyFeatureDataSourceAsEmpty(input_datasource, output_path, overwrite=overwrite, new_srs=to_srs)
    reproj_layer = reproj_ds.GetLayer()

    in_feature = input_layer.GetNextFeature()
    while in_feature:
        geom = in_feature.GetGeometryRef()
        if geom:
            geom.Transform(transform)

        reproj_feature = ogr.Feature(layer_defn)
        reproj_feature.SetGeometry(geom)
        for i in range(layer_defn.GetFieldCount()):
            reproj_feature.SetField(layer_defn.GetFieldDefn(i).GetNameRef(), in_feature.GetField(i))
        reproj_layer.CreateFeature(reproj_feature)

        in_feature = input_layer.GetNextFeature()

    if ds:
        ds.Release()
        del input_layer, ds, input_datasource

    return reproj_ds


def reprojectRaster(input_raster, output_path, gdal_data_type=None, to_srs=None, new_cellsize=None,
                    interpolation=gdal.GRA_NearestNeighbour, overwrite=False):
    '''
    Reproject or resample a raster dataset.
    :param input_raster: (gdal.Dataset) The raster dataset to reproject/resample.
    :param output_path: (str) The filepath to save the reprojected/resampled raster.
    :param [gdal_data_type]: (int) If provided, the new data type for the raster, which must be value corresponding to
           gdal data type constant (e.g. `gdal.GDT_UInt16`).
    :param [to_srs]: (osr.SpatialReference) If provided, the new spatial referenced to reproject to.
    :param [new_cellsize]: (float[]) If provided, the new cellsize to resample at.
    :param [interpolation=gdal.GRA_NearestNeighbour]: The interpolation method used to reproject/resample the data. Must be
           value corresponding to valid gdal constant (e.g. `gdal.GRA_Bilinear`).
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return: (gdal.Dataset) The Dataset instance of the reprojected/resampled raster.
    '''
    from_srs_wkt = input_raster.GetProjectionRef()
    from_srs = osr.SpatialReference()
    from_srs.ImportFromWkt(from_srs_wkt)
    if to_srs:
        transform = osr.CoordinateTransformation(from_srs, to_srs)
    else:
        transform = None
        to_srs = from_srs

    driver = rasters.getRasterDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.Delete(output_path)

    origin, pixel_size, extent = rasters.getRasterTransform(input_raster)
    far_corner = [origin[0] + pixel_size[0] * extent[0], origin[1] + pixel_size[1] * extent[1]]

    reproj_top_left = transform.TransformPoint(origin[0], origin[1]) if transform else (origin[0], origin[1])
    reproj_btm_left = transform.TransformPoint(origin[0], far_corner[1]) if transform else (origin[0], far_corner[1])
    reproj_top_right = transform.TransformPoint(origin[0], origin[1]) if transform else (origin[0], origin[1])
    reproj_btm_right = transform.TransformPoint(far_corner[0], origin[1]) if transform else (far_corner[0], origin[1])

    min_max_x = [
        reproj_top_left[0] if reproj_top_left[0] < reproj_btm_left[0] else reproj_btm_left[0],
        reproj_top_right[0] if reproj_top_right[0] > reproj_btm_right[0] else reproj_btm_right[0]
    ]
    min_max_y = [
        reproj_btm_left[1] if reproj_btm_left[1] < reproj_btm_right[1] else reproj_btm_right[1],
        reproj_top_left[1] if reproj_top_left[1] > reproj_top_right[1] else reproj_top_right[1]
    ]

    reproj_origin = [
        min_max_x[0] if pixel_size[0] > 0 else min_max_x[1],
        min_max_y[0] if pixel_size[1] > 0 else min_max_y[1]
    ]
    if not new_cellsize:
        new_cellsize[0] = pixel_size[0]
        new_cellsize[1] = pixel_size[1]
    reproj_width = abs(math.ceil((min_max_x[1] - min_max_x[0]) / float(new_cellsize[0])))
    reproj_height = abs(math.ceil((min_max_y[1] - min_max_y[0]) / float(new_cellsize[1])))

    reproj_raster = driver.Create(output_path, int(reproj_width), int(reproj_height), input_raster.RasterCount, gdal_data_type)
    reproj_raster.SetGeoTransform(rasters.createRasterTransform(reproj_origin, new_cellsize))
    reproj_raster.SetProjection(to_srs.ExportToWkt())

    rp = gdal.ReprojectImage(input_raster, reproj_raster, from_srs.ExportToWkt(), to_srs.ExportToWkt(), interpolation)

    check_color_table = gdal_data_type == gdal.GDT_UInt16 or gdal_data_type == gdal.GDT_Byte
    for b in range(input_raster.RasterCount):
        band = input_raster.GetRasterBand(b+1)
        reproj_band = reproj_raster.GetRasterBand(b+1)
        no_data_val = band.GetNoDataValue()
        if no_data_val is not None:
            reproj_band.SetNoDataValue(no_data_val)
        if check_color_table:
            color_table = band.GetRasterColorTable()
            if color_table:
                reproj_band.SetRasterColorTable(color_table)

    return reproj_raster
