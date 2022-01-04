import os
from osgeo import ogr


SHAPEFILE_DRIVER_NAME = "ESRI Shapefile"
POSTGRESQL_DRIVER_NAME = "PostgreSQL"
GEODATABASE_DRIVER_NAME = "OpenFileGDB"  # "FileGDB"
SDE_DRIVER_NAME = "SDE"


def _getLayer(datasource, for_write=False, allow_path=False):
    '''
    Copied from lib._getlayer.py (otherwise circular import results)
    '''
    if isinstance(datasource, ogr.DataSource):
        return datasource.GetLayer(), None
    elif isinstance(datasource, ogr.Layer):
        return datasource, None
    elif allow_path and isinstance(datasource, str):
        datasource = features.getFeatureDataSource(datasource, write=for_write)
        layer = datasource.GetLayer()
        return layer, datasource
    else:
        raise Exception("Must supply ogr DataSource or Layer as input")


def guessFeatureDriver(path):
    '''
    Guess feature driver by filename (or database conn string). Limited support, still needs fleshing out. Defaults to
    shapefile if it cannot be correctly determined.
    :param path: (str) Filepath or conn string.
    :return: (str) OGR feature driver name.
    '''
    if path.startswith("PG:"):
        return POSTGRESQL_DRIVER_NAME
    elif path.find(".shp") >= 0:
        return SHAPEFILE_DRIVER_NAME
    elif path.find(".gdb") >= 0:
        return GEODATABASE_DRIVER_NAME
    elif path.find(".sde") >= 0:
        return SDE_DRIVER_NAME
    else:
        return SHAPEFILE_DRIVER_NAME


def getFeatureDriver(path):
    '''
    Get feature driver by filename (or database conn string). Limited support, still needs fleshing out. Defaults to
    shapefile if it cannot be correctly determined.
    :param path: (str) Filepath or conn string.
    :return: (ogr.Driver)
    '''
    return ogr.GetDriverByName(guessFeatureDriver(path))


def getFeatureDataSource(path_or_datasource, driver_name=None, write=False):
    '''
    Get feature datasource as ogr.DataSource instance.
    :param path_or_datasource: (str|ogr.DataSource) The filepath. If provided as DataSource already, just returns that.
    :param [driver_name]: (str) The driver name. If not provided, attempts to guess via guessFeatureDriver(), which has
           limited support.
    :param [write=False]: (boolean) Set to True if write privileges are requried. Otherwise opens as ready-only.
    :return: (ogr.DataSource)
    '''
    if isinstance(path_or_datasource, ogr.DataSource):
        return path_or_datasource
    driver = getFeatureDriver(path_or_datasource) if driver_name is None else ogr.GetDriverByName(driver_name)
    return driver.Open(path_or_datasource, 1 if write else 0)


def getFeatureExtent(feature):
    '''
    Get the feature extent/envelope.
    :param feature: (ogr.Feature) Feature of interest.
    :return: Tuple of numbers in order of: x-min, x-max, ymin, and y-max.
    '''
    env = feature.GetGeometryRef().GetEnvelope()
    xmin = env[0]
    xmax = env[1]
    ymin = env[2]
    ymax = env[3]
    return xmin, xmax, ymin, ymax


def copyFeatureDataSourceAsEmpty(copy_datasource, output_path, overwrite=False, new_srs=None, new_geom_type=None):
    '''
    Copy a feature datasource as empty. That is, creates empty copy with same spatial reference system and fields, but
    with no features.
    :param copy_datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource to copy. May be provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param output_path: (str) The output path to save the copied datasource at.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [new_srs]: (osr.SpatialReference) If provided, changes the spatial reference in the copied datasource.
    :param [new_geom_type]: (int) If provided, changes the geometry type in the copied datasource. The geometry type
           must be from one of the constant values in OGR relevant to geometry types (e.g. `ogr.wkbPolygon`).
    :return: (ogr.DataSource) The DataSource instance of the new, copied datasource.
    '''
    copy_layer, copy_ds = _getLayer(copy_datasource, allow_path=True)
    driver = getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)

    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(
        copy_layer.GetName(),
        copy_layer.GetSpatialRef() if new_srs is None else new_srs,
        copy_layer.GetGeomType() if not new_geom_type else new_geom_type
    )
    if not layer:
        raise Exception("Error creating layer: {0} [{1}]".format(copy_layer.GetName(), copy_layer.GetGeomType()))

    copy_layer_defn = copy_layer.GetLayerDefn()
    for i in range(copy_layer_defn.GetFieldCount()):
        field_defn = copy_layer_defn.GetFieldDefn(i)
        layer.CreateField(field_defn)

    if copy_ds:
        copy_ds.Release()
        del copy_ds
    return ds


def createFeatureDataSource(output_path, layer_name, srs, geom_type, add_fields=None, overwrite=False):
    '''
    Create a new feature datasource.
    :param output_path: (str) The output path to save the new datasource at.
    :param layer_name: (str) The layer name.
    :param srs: (ogr.SpatialReference) The spatial reference.
    :param geom_type: (int) The geometry type from one of the constant values in OGR relevant to geometry types (e.g.
           `ogr.wkbPolygon`).
    :param [add_fields]: (ogr.FieldDefn[]) The fields to create.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return: (ogr.DataSource) The DataSource instance of the new datasource.
    '''
    driver = getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)

    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(layer_name, srs, geom_type)

    if add_fields:
        for f in add_fields:
            layer.CreateField(f)

    return ds


def count(datasource):
    '''
    Get a count of features within a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource of interest. May be provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :return: (int)
    '''
    layer, ds = _getLayer(datasource, allow_path=True)
    count = layer.GetFeatureCount()
    if ds:
        ds.Release()
        del layer, ds
    return count


def forEachFeature(datasource, callback, for_write=False):
    '''
    Run a callback function on each feature in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource of interest. May be provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param callback: Callback function run on each feature. Provided single parameter of ogr.Feature.
    :param [for_write]: (boolean) If datasource was provided as a path, function will handle opening datasource
           internally. Ifcallback writes to this datasource, set this to True to ensure write privilege.
    :return:
    '''
    layer, ds = _getLayer(datasource, allow_path=True, for_write=for_write)
    layer.SetNextByIndex(0)
    feat = layer.GetNextFeature()
    while feat:
        if callback(feat):
            break
        feat = layer.GetNextFeature()
    layer.SetNextByIndex(0)
    if ds:
        ds.Release()
        del layer, ds


def makeValid(datasource):
    '''
    Attempts to validate invalid geometries without losing vertices.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource of interest. May be provided as
           ogr.DataSource, ogr.Layer, or filepath.
    '''
    layer, ds = _getLayer(datasource, allow_path=True, for_write=True)
    i = 0
    layer.SetNextByIndex(0)
    feat = layer.GetNextFeature()
    while feat:
        geom = feat.GetGeometryRef()
        vgeom = geom.MakeValid()
        if not vgeom:
            raise Exception("Error validating geometry for feature {0}".format(i))
        feat.SetGeometry(vgeom)
        layer.SetFeature(feat)
        feat = layer.GetNextFeature()
        i += 1
    layer.SetNextByIndex(0)
    if ds:
        ds.Release()
        del layer, ds
