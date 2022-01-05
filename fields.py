from osgeo import ogr
from date import date
from lib._getlayer import get as _get_layer
from Field import Field


# type name gets overwritten by method so reassign for later use
_list             = list
# generic FID field instance
FIELD_FID         = Field(is_fid=True)
# geometry type constants
LENGTH_METER      = 1101
LENGTH_KILOMETER  = 1102
LENGTH_FEET       = 2101
LENGTH_YARD       = 2102
LENGTH_MILE       = 2103
LENGTH_NMILE      = 2104
AREA_SQ_METER     = 100+LENGTH_METER
AREA_SQ_KILOMETER = 100+LENGTH_KILOMETER
AREA_SQ_FEET      = 100+LENGTH_FEET
AREA_SQ_MILE      = 100+LENGTH_MILE
AREA_HECTARE      = 1255
AREA_ACRE         = 2255


def definition(datasource, field_name=None):
    '''
    Get field definition.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param [field_name]: (str) The field name to search for. If not provided, returns all existing fields in datasource.
    :return: (ogr.FieldDefn|ogr.FieldDefn[]) The field definition (or None if not found), or a list of all fields as
             field definition if no specific field name provided.
    '''
    layer, ds = _get_layer(datasource, allow_path=True)
    defn = layer.GetLayerDefn()
    def _final(ds, ret=None):
        if ds:
            ds.Release()
            del ds
        return ret
    if field_name:
        f_index = defn.GetFieldIndex(field_name)
        if f_index < 0:
            return None
        return _final(ds, defn.GetFieldDefn(f_index))
    else:
        fields = []
        for i in range(defn.GetFieldCount()):
            fields.append(defn.GetFieldDefn(i))
        return _final(ds, fields)


def list(datasource):
    '''
    Get list of all fields in datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :return: (common.Field[]) List of Field instances.
    '''
    layer, ds = _get_layer(datasource, allow_path=True)
    defn = layer.GetLayerDefn()
    fields = []
    for i in range(defn.GetFieldCount()):
        fdefn = defn.GetFieldDefn(i)
        fields.append(get(layer, fdefn))
    if ds:
        ds.Release()
        del ds
    return fields


def exists(datasource, field_name):
    '''
    Search for a field in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param field_name: (str) The field name to search for.
    :return: (common.Field) The field instance, or None if not present in datasource.
    '''
    return find(datasource, field_name)


def find(datasource, field_name):
    '''
    Search for a field in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param field_name: (str) The field name to search for.
    :return: (common.Field) The field instance, or None if not present in datasource.
    '''
    layer, ds = _get_layer(datasource, allow_path=True)
    defn = layer.GetLayerDefn()
    match = False
    for i in range(defn.GetFieldCount()):
        fdefn = defn.GetFieldDefn(i)
        if fdefn.GetName() == field_name:
            match = get(layer, fdefn)
            break
    if ds:
        ds.Release()
        del ds
    return match


def get(datasource, field, must_exist=True):
    '''
    Get the Field instance in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
        filepath.
    :param field: (common.Field|ogr.FieldDefn|str) The input field, which may be instance of Field, ogr.FieldDefn, or
           the field name.
    :param [must_exist=True]: If true, throws exception if field does not exist in datasource.
    :return: (common.Field) The field instance.
    '''
    if field == FIELD_FID:
        return field
    if isinstance(field, Field):
        return field
    layer, ds = _get_layer(datasource, allow_path=True)
    defn = layer.GetLayerDefn()
    try:
        if isinstance(field, ogr.FieldDefn):
            return Field(fdefn=field, lyr_defn=defn, must_exist=must_exist)
        elif isinstance(field, str):
            return Field(field_name=field, lyr_defn=defn, must_exist=must_exist)
        else:
            raise Exception("Field must be supplied as ogr.FieldDefn or field name.")
    finally:
        if ds:
            ds.Release()
            del ds


def value(feature, field):
    '''
    Get the value of a field for a particular feature.
    :param feature: (ogr.Feature) The feature of interest.
    :param field: (common.Field) The field for which to grab the value of.
    :return: (str|int|float|datetime) The value.
    '''
    if not isinstance(field, Field):
        raise Exception("Must provide common.Field instance as field.")
    if field.is_fid:
        return feature.GetFID()
    if field.type in ("String", ogr.OFTString, str):
        return feature.GetFieldAsString(field.index)
    elif field.type in ("Integer", "Integer32", "Integer64", ogr.OFTInteger, ogr.OFTInteger64, int):
        return feature.GetFieldAsInteger(field.index)
    elif field.type in ("Real", ogr.OFTReal, float):
        return feature.GetFieldAsDouble(field.index)
    elif field.type in ("DateTime", "Date", ogr.OFTDate, ogr.OFTDateTime, date):
        return feature.GetFieldAsDateTime(field.index)
    else:
        raise Exception("Unrecognized field type: {0}".format(field.type))


def values(datasource, fields):
    '''
    Get the values of a field or fields for all features in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param fields: (common.Field[]) The fields for which to grab the values of.
    :return: (dict[]) The list of values, with each set of values (per row/feature) being a dictionary of field names to
             associated value.
    '''
    if not isinstance(fields, (_list, tuple)):
        fields = [fields]
    layer, ds = _get_layer(datasource, allow_path=True)
    fields = [get(layer, f) for f in fields]

    def build_lambda(for_field):
        if not isinstance(for_field, Field):
            raise Exception("Must provide common.Field instance as field.")
        if for_field.is_fid:
            return lambda feat: feat.GetFID()
        elif for_field.type in ("String", ogr.OFTString, str):
            return lambda feat: feat.GetFieldAsString(for_field.index)
        elif for_field.type in ("Integer", "Integer32", "Integer64", ogr.OFTInteger, ogr.OFTInteger64, int):
            return lambda feat: feat.GetFieldAsInteger(for_field.index)
        elif for_field.type in ("Real", ogr.OFTReal, float):
            return lambda feat: feat.GetFieldAsDouble(for_field.index)
        elif for_field.type in ("DateTime", "Date", ogr.OFTDate, ogr.OFTDateTime, date):
            return lambda feat: feat.GetFieldAsDateTime(for_field.index)
        else:
            raise Exception("Unrecognized field type: {0}".format(for_field.type))

    lambdas = {f.name: build_lambda(f) for f in fields}

    fvalues = []
    layer.SetNextByIndex(0)
    for feat in layer:
        fvalues.append({fname: getter(feat) for fname, getter in lambdas.items()})
    del feat
    layer.SetNextByIndex(0)

    if ds:
        ds.Release()
        del layer, ds

    return fvalues


def set_value(feature, field, value):
    '''
    Set the value of a field, for a particular feature.
    :param feature: (ogr.Feature) The feature to set the value of.
    :param field: (common.Field) The field to set the value in.
    :param value: The value to set
    '''
    if not isinstance(field, Field):
        raise Exception("Must provide common.Field instance as field.")
    if field.is_fid:
        feature.SetFID(value)
    elif value is None:
        feature.SetFieldNull(field.name)
    else:
        feature.SetField(field.name, value)


def create_defn(name, field_type, width=0, precision=0):
    return create_definition(name, field_type, width, precision)


def create_definition(name, field_type, width=0, precision=0):
    '''
    Create an ogr.FieldDefn.
    :param name: (str) The field name.
    :param field_type: The field type. May provide a type (e.g. int), a string (e.g. "Integer64"), or an int value that
           matches on of the type constants in OGR (e.g. ogr.OFTReal).
    :param [width]: (int) The field width.
    :param [precision]: (int) The field precision.
    :return: (ogr.FieldDefn)
    '''
    ogr_type = None
    if field_type == str:
        ogr_type = ogr.OFTString
    elif field_type == int:
        ogr_type = ogr.OFTInteger64
    elif field_type == float:
        ogr_type = ogr.OFTReal
    elif field_type == date:
        ogr_type = ogr.OFTDateTime
    elif isinstance(field_type, str):
        if field_type == "String":
            ogr_type = ogr.OFTString
        elif field_type == "Integer32":
            ogr_type = ogr.OFTInteger
        elif field_type == "Integer64":
            ogr_type = ogr.OFTInteger64
        elif field_type == "Integer":
            ogr_type = ogr.OFTInteger64
        elif field_type == "Float":
            ogr_type = ogr.OFTReal
        elif field_type == "Double":
            ogr_type = ogr.OFTReal
        elif field_type == "Real":
            ogr_type = ogr.OFTReal
        elif field_type == "DateTime":
            ogr_type = ogr.OFTDateTime
        elif field_type == "Date":
            ogr_type = ogr.OFTDate
        else:
            raise Exception("Unknown field type supplied")
    elif not isinstance(field_type, int):
        raise Exception("Unknown field type supplied")
    defn = ogr.FieldDefn(name, ogr_type)
    if width:
        defn.SetWidth(width)
    if precision:
        defn.SetPrecision(precision)
    return defn


def create(datasource, name, field_type, width=0, precision=0):
    '''
    Create a new field in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param name: (str) The field name.(class|str|int)
    :param field_type: The field type. May provide a type (e.g. int), a string (e.g. "Integer64"), or an int value that
           matches on of the type constants in OGR (e.g. ogr.OFTReal).
    :param [width]: (int) The field width.
    :param [precision]: (int) The field precision.
    :return:
    '''
    return add(datasource, name, field_type, width, precision)


def add(datasource, name, type, width=0, precision=0):
    '''
    Create a new field in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param name: (str) The field name.(class|str|int)
    :param field_type: The field type. May provide a type (e.g. int), a string (e.g. "Integer64"), or an int value that
           matches on of the type constants in OGR (e.g. ogr.OFTReal).
    :param [width]: (int) The field width.
    :param [precision]: (int) The field precision.
    :return: (common.Field) The new field as a Field instance.
    '''
    layer, ds = _get_layer(datasource, allow_path=True, for_write=True)
    defn = create_definition(name, type, width, precision)
    layer.CreateField(defn)
    field = get(layer, defn)
    if ds:
        ds.Release()
        del layer, ds
    return field


def calculate(datasource, on_field, use_fields, calc_callback):
    '''
    Calculate a field for all feature in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param on_field: (common.Field|ogr.FieldDefn|str) The field to calculate, which may be instance of Field,
           ogr.FieldDefn, or the field name. Must already exist.
    :param use_fields: A list of fields for which values will be obtained and sent to the callback function. Like
           `on_field`, may contain instances of Field, ogr.FieldDefn, or field names. Can be None if not needed.
    :param calc_callback: (callback) Callback function which returns the value to calculate for each feature. Provided
           three parameters: `i` (feature index), `feat` (the ogr.Feature instance), and `values` (list) a list of
           values for the feature corresponding to `use_field`.
    '''
    layer, ds = _get_layer(datasource, allow_path=True, for_write=True)
    field = get(layer, on_field)

    if use_fields and len(use_fields):
        get_fields = [get(layer, f) for f in use_fields]
    else:
        get_fields = None

    layer.SetNextByIndex(0)
    i = 0
    for feat in layer:
        fvalues = [value(feat, field) for field in get_fields] if get_fields else []
        set_value(feat, field, calc_callback(i, feat, fvalues))
        i += 1
    del feat
    layer.SetNextByIndex(0)

    if ds:
        ds.Release()
        del layer, ds


def calc_geometry(datasource, field_name, units):
    '''
    Calculate a geometry field (e.g. length or area) for all features in a datasource.
    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource, provided as ogr.DataSource, ogr.Layer, or
           filepath.
    :param field_name: (str) The name of the field in which to put values. Will be created if does not exist.
    :param units: (int) The geometry unit type. See constants in this module.
    :return:
    '''
    layer, ds = _get_layer(datasource, allow_path=True, for_write=True)
    try:
        srs = layer.GetSpatialRef()
        if not srs.IsProjected():
            raise Exception("Unprojected spatial reference system. Reproject datasource first.")

        field = get(layer, field_name, must_exist=False)
        if field.is_fid:
            raise Exception("Cannot calculate geometry to FID field.")
        elif field.index < 0:
            field = create(layer, field_name, float)

        length = srs.GetLinearUnitsName().lower()
        if length in ["meter", "meters", "metre", "metres"]:
            multiplier = 1
        elif length in ["feet", "foot"]:
            multiplier = 0.092903
        else:
            raise Exception("Unrecognized unit in spatial reference: {0}".format(length))
        gtype = 1
        if units == LENGTH_METER:
            pass
        elif units == AREA_SQ_METER:
            gtype = 2
        elif units == LENGTH_KILOMETER:
            multiplier *= 1e-3
        elif units == LENGTH_FEET:
            multiplier *= 3.28084
        elif units == LENGTH_YARD:
            multiplier *= 1.09361
        elif units == LENGTH_MILE:
            multiplier *= 6.21371e-4
        elif units == LENGTH_NMILE:
            multiplier *= 5.39957e-4
        elif units == AREA_SQ_KILOMETER:
            gtype = 2
            multiplier *= 1e-6
        elif units == AREA_HECTARE:
            gtype = 2
            multiplier *= 1e-4
        elif units == AREA_SQ_FEET:
            gtype = 2
            multiplier *= 10.7639
        elif units == AREA_SQ_MILE:
            gtype = 2
            multiplier *= 3.86102e-7
        elif units == AREA_ACRE:
            gtype = 2
            multiplier *= 2.47105e-4
        else:
            raise Exception("Unrecognized unit provided.")

        layer.SetNextByIndex(0)
        feat = layer.GetNextFeature()
        while feat:
            geom = feat.GetGeometryRef()
            gvalue = 0
            if gtype == 1:
                gvalue = geom.Length()*multiplier if geom else 0
            elif gtype == 2:
                gvalue = geom.Area()*multiplier if geom else 0
            feat.SetField(field.name, gvalue)
            layer.SetFeature(feat)
            feat = layer.GetNextFeature()
        layer.SetNextByIndex(0)

        return field
    finally:
        if ds:
            ds.Release()
            del layer, ds


def join(datasource, on_field, join_datasource, to_field, join_fields, error_if_many=True):
    '''

    :param datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource on which the join will originate and joined
           fields be added, provided as ogr.DataSource, ogr.Layer, or filepath.
    :param on_field: (common.Field|ogr.FieldDefn|str) The field join on in the datasource of origin. May be instance of
           Field, ogr.FieldDefn, or the field name.
    :param join_datasource: (ogr.DataSource|ogr.Layer|str) The feature datasource on which to join, provided as
           ogr.DataSource, ogr.Layer, or filepath.
    :param to_field: (common.Field|ogr.FieldDefn|str) The field join on in the datasource being joined. May be instance of
           Field, ogr.FieldDefn, or the field name.
    :param join_fields: (common.Field[]|ogr.FieldDefn[]|str[]) The fields on the join datasource to add to the datasource of
           origin. Provided as list of any combination of instances of Field, ogr.FieldDefn, or field names.
    :param [error_if_many=True]: If True, errors if there are joins that break the one-to-one relationship. If False,
           the joined data will simply be from the last valid join found for each feature, if multiple joins exist.
    '''
    og_layer, ds1 = _get_layer(datasource, allow_path=True, for_write=True)
    og_field      = get(og_layer, on_field)
    to_layer, ds2 = _get_layer(join_datasource)
    to_field      = get(to_layer, to_field)
    join_fields   = [get(to_layer, f) for f in join_fields]

    if not og_field:
        raise Exception("Join on field does not exist in datasource")
    if not to_field:
        raise Exception("Join to field does not exist in join datasource")
    if None in join_fields:
        raise Exception("One or more join fields do not exist in join datasource")

    join_map = {}

    i = 0
    to_layer.SetNextByIndex(0)
    for feat in to_layer:
        join_on = value(feat, to_field)
        if join_on in join_map and error_if_many:
            raise Exception("Value ({0}) has more than one join in join datasource.".format(join))
        join_map[join_on] = i
        i += 1
    del feat
    to_layer.SetNextByIndex(0)

    copy_fields = []
    for join_field in join_fields:
        if not join_field.is_fid:
            og_layer.CreateField(join_field.defn)
            copy_fields.append(join_field)
        else:
            i = 0
            join_fid_field_name = "JOIN_FID"
            while exists(og_layer, join_fid_field_name):
                i += 1
                join_fid_field_name = "JOIN_FID_{0}".format(i)
            copy_fields.append(create(og_layer, join_fid_field_name, int))

    og_layer.SetNextByIndex(0)
    for og_feat in og_layer:
        join_to = value(og_layer, og_field)
        if join_to not in join_map:
            continue
        join_to_feat = to_layer.GetFeature(join_map[join_to])
        for f in range(len(join_fields)):
            set_value(og_feat, copy_fields[f], value(join_to_feat, join_fields[f]))
    del og_feat
    og_layer.SetNextByIndex(0)

    if ds1:
        ds1.Release()
        del og_layer, ds1
    if ds2:
        ds2.Release()
        del to_layer, ds2
