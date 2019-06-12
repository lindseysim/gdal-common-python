import os

import ogr
from datetime import datetime

SHAPEFILE_DRIVER_NAME = "ESRI Shapefile"
POSTGRESQL_DRIVER_NAME = "PostgreSQL"
GEODATABASE_DRIVER_NAME = "OpenFileGDB"  # "FileGDB"
SDE_DRIVER_NAME = "SDE"


def guessFeatureDriver(path):
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
    return ogr.GetDriverByName(guessFeatureDriver(path))


def getFeatureDataset(path_or_dataset, driver_name=None, write=False):
    if isinstance(path_or_dataset, ogr.DataSource):
        return path_or_dataset
    driver = getFeatureDriver(path_or_dataset) if driver_name is None else ogr.GetDriverByName(driver_name)
    return driver.Open(path_or_dataset, 1 if write else 0)


def getFeatureExtent(feature):
    env = feature.GetGeometryRef().GetEnvelope()
    xmin = env[0]
    xmax = env[1]
    ymin = env[2]
    ymax = env[3]
    return xmin, xmax, ymin, ymax


def getFields(dataset):
    if isinstance(dataset, ogr.Layer):
        layer = dataset
    elif isinstance(dataset, ogr.DataSource):
        layer = dataset.GetLayer()
    else:
        raise Exception("Input datasets must be instance of ogr Layer or DataSource")
    defn = layer.GetLayerDefn()
    fields = []
    for i in range(defn.GetFieldCount()):
        f_defn = defn.GetFieldDefn(i)
        fields.append(
            {
                'name': f_defn.GetName(),
                'type': f_defn.GetFieldTypeName(f_defn.GetType()),
                'width': f_defn.GetWidth(),
                'precision': f_defn.GetPrecision()
            }
        )
    return fields


def getFieldDefinition(feature_layer, field_name):
    defn = feature_layer.GetLayerDefn()
    f_index = defn.GetFieldIndex(field_name)
    if f_index < 0:
        return None
    return defn.GetFieldDefn(f_index)


def getField(feature_layer, field_name):
    defn = feature_layer.GetLayerDefn()
    f_index = defn.GetFieldIndex(field_name)
    if f_index < 0:
        return None, None, None
    f_defn = defn.GetFieldDefn(f_index)
    return field_name, f_index, f_defn.GetFieldTypeName(f_defn.GetType())


def getUniqueField(feature_layer, unique_field=None):
    defn = feature_layer.GetLayerDefn()
    if unique_field is None:
        # try to determine FID column
        unique_field = feature_layer.GetFIDColumn()
        if unique_field == "":
            # if none specified in file, try common column names
            for try_field in ["FID", "OID", "OBJECTID", "FEATUREID", "ID", None]:
                if try_field is None:
                    raise Exception(
                        "Could not automatically determine FID column, must supply unique field in parameter.")
                unique_field = try_field
                f_index = defn.GetFieldIndex(unique_field)
                if f_index >= 0:
                    break
    else:
        f_index = defn.GetFieldIndex(unique_field)
        if f_index < 0:
            raise Exception("Could not find field (" + unique_field + ") in feature layer.")
    f_defn = defn.GetFieldDefn(f_index)
    return unique_field, f_index, f_defn.GetFieldTypeName(f_defn.GetType())


def getFieldValue(feature, field_defn):
    if isinstance(field_defn, ogr.FieldDefn):
        field_name = field_defn.GetNameRef()
        field_type = field_defn.GetFieldTypeName(field_defn.GetType())
    elif isinstance(field_defn, dict):
        field_name = field_defn['name']
        field_type = field_defn['type']
    else:
        raise Exception(
            "Field definition must be supplied as ogr.FieldDefn or as dictionary with keys 'name' and 'type'")

    if field_type == "String" or field_type == ogr.OFTString or field_type == basestring:
        return feature.GetFieldAsString(field_name)
    elif field_type == "Integer" or field_type == "Integer64" or field_type == ogr.OFTInteger \
            or field_type == ogr.OFTInteger64 or field_type == int or field_type == long:
        return feature.GetFieldAsInteger(field_name)
    elif field_type == "Real" or field_type == ogr.OFTReal or field_type == float:
        return feature.GetFieldAsDouble(field_name)
    elif field_type == "DateTime" or field_type == "Date" or field_type == ogr.OFTDate or field_type == ogr.OFTDateTime \
            or field_type == datetime:
        return feature.GetFieldAsDateTime(field_name)
    else:
        raise Exception("Unrecognized field type: {0}".format(field_type))


def createFieldDefinition(name, field_type):
    if field_type == basestring:
        ogr_type = ogr.OFTString
    elif field_type == int:
        ogr_type = ogr.OFTInteger
    elif field_type == long:
        ogr_type = ogr.OFTInteger64
    elif field_type == float:
        ogr_type = ogr.OFTReal
    elif field_type == datetime:
        ogr_type = ogr.OFTDateTime
    elif isinstance(field_type, (int, long)):
        ogr_type = field_type
    elif isinstance(field_type, basestring):
        if field_type == "String":
            ogr_type = ogr.OFTString
        elif field_type == "Integer":
            ogr_type = ogr.OFTInteger
        elif field_type == "Integer64":
            ogr_type = ogr.OFTInteger64
        elif field_type == "Real":
            ogr_type = ogr.OFTReal
        elif field_type == "DateTime":
            ogr_type = ogr.OFTDateTime
        elif field_type == "Date":
            ogr_type = ogr.OFTDate
        else:
            raise Exception("Unknown field type supplied")
    else:
        raise Exception("Unknown field type supplied")
    return ogr.FieldDefn(name, ogr_type)


def copyFeatureDatasetAsEmpty(copy_dataset, output_path, overwrite=False, new_srs=None):
    if isinstance(copy_dataset, ogr.DataSource):
        copy_layer = copy_dataset.GetLayer()
    elif isinstance(copy_dataset, ogr.Layer):
        copy_layer = copy_dataset
    else:
        raise Exception("Must supply ogr DataSource or Layer as input")

    driver = getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)

    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(
        copy_layer.GetName(),
        copy_layer.GetSpatialRef() if new_srs is None else new_srs,
        copy_layer.GetGeomType()
    )

    copy_layer_defn = copy_layer.GetLayerDefn()
    for i in range(copy_layer_defn.GetFieldCount()):
        field_defn = copy_layer_defn.GetFieldDefn(i)
        layer.CreateField(field_defn)

    return ds


def createFeatureDataset(output_path, layer_name, srs, geom_type, fields=None, overwrite=False):
    driver = getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)

    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(layer_name, srs, geom_type)

    if fields:
        for f in fields:
            layer.CreateField(
                f if isinstance(f, ogr.FieldDefn) else createFieldDefinition(f['name'], f['type'])
            )

    return ds

def forEachFeature(feature_layer, callback):
    feature_layer.SetNextByIndex(0)
    feat = feature_layer.GetNextFeature()
    while feat:
        if callback(feat):
            break
        feat = feature_layer.GetNextFeature()
    feature_layer.SetNextByIndex(0)
