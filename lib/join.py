from .. import fields
from . import _rectifyinputs as rectify


def intersect(input_datasource, input_id_field, join_datasource, join_fields, tmp_reproj_path=None, overwrite=False,
              delete_tmp_files=True):
    '''
    Get joined data from two feature datasources by intersection. Returns assuming one-to-many relations are possible.
    :param input_datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource of origin, provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param input_id_field: (common.Field|ogr.FieldDefn|str) The input ID field which will become the keys to returned
           dictionary. As such, values must be unique or entries will be overwritten. May be provided as instance of
           Field, ogr.FieldDefn, or the field name. If None, assumes the FID field.
    :param join_datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource to join to, provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param join_fields: (common.Field[]|ogr.FieldDefn[]|str[]) The fields from the join datasource to return as the
           joined data. May be provided as list containing instances of Field, ogr.FieldDefn, or field names.
    :param [tmp_reproj_path=None]: (str) If input and join datasources have differing spatial references, the join
           datasource will need to be reprojected first, which it will do to this filepath or folderpath. The temporary
           datasource will be removed after the function completes.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :param [delete_tmp_files=True]: (boolean) If False, won't delete temporary file created if reprojection of join
           data source was necessary.
    :return: (dict) Dictionary keys will be unique values in the input datasource for the ID field identified. The
             values will be a list of all matches from intersection with join data source. Each item in the list will be
             another dictionary of field names to values for each match.
    '''
    process_objs = rectify.rectify(input_datasource, join_datasource, None, tmp_reproj_path, overwrite=overwrite)
    input_layer  = process_objs['input_layer']
    id_field     = fields.get(input_layer, input_id_field if input_id_field else fields.FIELD_FID)
    join_layer   = process_objs['method_layer']
    join_fields  = [fields.get(join_layer, f) for f in join_fields]

    if not id_field:
        raise Exception("Join ID field does not exist in datasource")
    if None in join_fields:
        raise Exception("One or more join fields do not exist in join datasource")

    join_map = {}
    input_layer.SetNextByIndex(0)
    feat = input_layer.GetNextFeature()
    while feat:
        geom = feat.GetGeometryRef()
        if geom:
            id = fields.value(feat, id_field)
            join_map[id] = []

            join_layer.SetNextByIndex(0)
            jfeat = join_layer.GetNextFeature()
            while jfeat:
                jgeom = jfeat.GetGeometryRef()
                if jgeom and geom.Intersects(jgeom):
                    join_map[id].append({f.name: fields.value(jfeat, f) for f in join_fields})
                jfeat = join_layer.GetNextFeature()
            join_layer.SetNextByIndex(0)

        feat = input_layer.GetNextFeature()
    input_layer.SetNextByIndex(0)

    rectify.cleanup(process_objs, delete_tmp_files)
    return join_map
