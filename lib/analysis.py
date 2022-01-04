import os
from osgeo import ogr
from .. import fields, features
from . import _rectifyinputs as rectify
from ._getlayer import get as _getLayer


def buffer(input_datasource, buffer_distance, output_path, overwrite=False):
    '''
    Clip features.
    :param input_datasource: (ogr.DataSource) The input features to be buffered.
    :param buffer_distance: (float) The buffer distance in same units as input SRS.
    :param output_path: (str) Path of output feature datasource.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    layer, ds = _getLayer(input_datasource, allow_path=True)

    driver = features.getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)

    buffer_ds = driver.CreateDataSource(output_path)
    buffer_layer = buffer_ds.CreateLayer(layer.GetName(), layer.GetSpatialRef(),  layer.GetGeomType())

    defn = layer.GetLayerDefn()
    copyfields = []
    for i in range(defn.GetFieldCount()):
        fdefn = defn.GetFieldDefn(i)
        buffer_layer.CreateField(fdefn)
        copyfields.append(fields.get(ds, fdefn))

    layer.SetNextByIndex(0)
    feat = layer.GetNextFeature()
    while feat:
        geom = feat.GetGeometryRef()
        buffgeom = geom.Buffer(buffer_distance)
        bufffeat = ogr.Feature(layer.GetLayerDefn())
        bufffeat.SetGeometry(buffgeom)
        for f in copyfields:
            fields.setValue(bufffeat, f, fields.value(feat, f))
        buffer_layer.CreateFeature(bufffeat)
        feat = layer.GetNextFeature()
    layer.SetNextByIndex(0)

    if ds:
        ds.Release()
        del ds, input_datasource
    return buffer_ds


def clip(input_datasource, clip_datasource, output_path, tmp_reproj_path=None, overwrite=False, delete_tmp_files=True):
    '''
    Clip features.
    :param input_datasource: (ogr.DataSource) The input features to be clipped.
    :param clip_datasource: (ogr.DataSource) The features to clip by.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs = rectify.rectify(input_datasource, clip_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer  = process_objs['input_layer']
    clip_layer   = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()
    input_layer.Clip(clip_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def erase(input_datasource, erase_datasource, output_path, tmp_reproj_path=None, overwrite=False,
          delete_tmp_files=True):
    '''
    Erase features.
    :param input_datasource: (ogr.DataSource) The input features to be erased.
    :param erase_datasource: (ogr.DataSource) The features to erase by.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs = rectify.rectify(input_datasource, erase_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer  = process_objs['input_layer']
    erase_layer  = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()
    input_layer.Erase(erase_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def identity(input_datasource, identity_datasource, output_path, tmp_reproj_path=None, overwrite=False,
             delete_tmp_files=True):
    '''
    Perform identity analysis on features.
    :param input_datasource: (ogr.DataSource) The input feature dataset.
    :param identity_datasource: (ogr.DataSource) The features to identify with.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs   = rectify.rectify(input_datasource, identity_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer    = process_objs['input_layer']
    identity_layer = process_objs['method_layer']
    output_ds      = process_objs['output_ds']
    output_layer   = output_ds.GetLayer()
    for field in fields.list(indentity_layer):
        if not fields.exists(output_layer, field.name):
            fields.create(output_layer, field.name, field.type)
    input_layer.Identity(identity_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def intersection(input_datasource, intersect_datasource, output_path, tmp_reproj_path=None, overwrite=False,
                 delete_tmp_files=True):
    '''
    Intersect features.
    :param input_datasource: (ogr.DataSource) The input feature dataset.
    :param intersect_datasource: (ogr.DataSource) The features to intersect with.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs    = rectify.rectify(input_datasource, intersect_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer     = process_objs['input_layer']
    intersect_layer = process_objs['method_layer']
    output_ds       = process_objs['output_ds']
    output_layer    = output_ds.GetLayer()
    for field in fields.list(intersect_layer):
        if not fields.exists(output_layer, field.name):
            fields.create(output_layer, field.name, field.type)
    input_layer.Intersection(intersect_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def symDifference(input_datasource, diff_datasource, output_path, tmp_reproj_path=None, overwrite=False,
                  delete_tmp_files=True):
    '''
    Perform symmetric difference on features features.
    :param input_datasource: (ogr.DataSource) The input feature dataset.
    :param diff_datasource: (ogr.DataSource) The features to difference with.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs = rectify.rectify(input_datasource, diff_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer  = process_objs['input_layer']
    diff_layer   = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()
    input_layer.SymDifference(diff_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def union(input_datasource, union_datasource, output_path, tmp_reproj_path=None, overwrite=False,
          delete_tmp_files=True):
    '''
    Union features. (Note behavior differs from ArcGIS union, as it does not create intersection splits).
    :param input_datasource: (ogr.DataSource) The input feature dataset.
    :param union_datasource: (ogr.DataSource) The features to union with.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs = rectify.rectify(input_datasource, union_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer  = process_objs['input_layer']
    union_layer  = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()
    input_layer.Union(union_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def update(input_datasource, update_datasource, output_path, tmp_reproj_path=None, overwrite=False,
           delete_tmp_files=True):
    '''
    Update features.
    :param input_datasource: (ogr.DataSource) The input feature dataset.
    :param update_datasource: (ogr.DataSource) The features to update with.
    :param output_path: (str) Path of output feature datasource.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (ogr.DataSource) The output feature Datsource.
    '''
    process_objs  = rectify.rectify(input_datasource, update_datasource, output_path, tmp_reproj_path, overwrite=overwrite)
    input_layer  = process_objs['input_layer']
    update_layer = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()
    input_layer.Update(update_layer, output_layer)
    rectify.cleanup(process_objs, delete_tmp_files)
    return output_ds


def nearTable(input_datasource, input_id_field, near_datasource, near_id_field, tmp_reproj_path=None, overwrite=False,
              delete_tmp_files=True, filter_callback=None):
    '''
    Get near table for every unique pair distance.
    :param input_datasource: (ogr.DataSource) The input feature dataset.
    :param input_id_field: (common.Field|ogr.FieldDefn|str) The input ID field to identify features in the input
           datasource. Should be unique. May be provided as instance of Field, ogr.FieldDefn, or the field name. If
           None, assumes the FID field.
    :param near_datasource: (ogr.DataSource) The datasource to compare distances against. It can be same as input
           datasource to determine pair distances between features within the same dataset.
    :param near_id_field: (common.Field|ogr.FieldDefn|str) The ID field to identify features in the near datasource.
           Should be unique. May be provided as instance of Field, ogr.FieldDefn, or the field name. If None, assumes
           the FID field.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :param [filter_callback]: (callback) Callback that may be used to filter features. Provided two paramters, the first
           is the ogr.Feature which may be from either input or near layer. The second is a simple integer, which is
           0 if from input layer, and 1 if from near layer. Return true to include said feature in analysis, false to
           exclude.
    :return:
    '''
    process_objs  = rectify.rectify(input_datasource, near_datasource, None, tmp_reproj_path, overwrite=overwrite)
    input_layer   = process_objs['input_layer']
    near_layer    = process_objs['method_layer']
    from_id_field = fields.get(input_datasource, input_id_field if input_id_field else fields.FIELD_FID)
    near_id_field = fields.get(near_datasource, near_id_field if input_id_field else fields.FIELD_FID)

    if not from_id_field:
        raise Exception("Input ID field does not exist.")
    if not near_id_field:
        raise Exception("Near ID field does not exist.")

    nfeats_input = input_layer.GetFeatureCount()
    nfeats_near = near_layer.GetFeatureCount()
    distances = []

    input_filter_ids = []
    near_filter_ids = []
    if filter_callback:
        i = 0
        while i < nfeats_input:
            feat = input_layer.GetFeature(i)
            if not filter_callback(feat, 0):
                input_filter_ids.append(i)
            i += 1
        i = 0
        while i < nfeats_near:
            feat = near_layer.GetFeature(i)
            if not filter_callback(feat, 1):
                near_filter_ids.append(i)
            i += 1

    ii = 0
    while ii < nfeats_input:
        feat = input_layer.GetFeature(ii)
        geom = feat.GetGeometryRef()
        if ii in input_filter_ids:
            ii += 1
            continue
        ni = 0
        while ni < nfeats_near:
            if ni in near_filter_ids:
                ni += 1
                continue
            nfeat = near_layer.GetFeature(ni)
            ngeom = nfeat.GetGeometryRef()
            distances.append({
                "FROM_ID":  fields.value(feat, from_id_field),
                "TO_ID":    fields.value(nfeat, near_id_field),
                "DISTANCE": geom.Distance(ngeom)
            })
            ni += 1
        ii += 1

    rectify.cleanup(process_objs, delete_tmp_files)

    return distances
