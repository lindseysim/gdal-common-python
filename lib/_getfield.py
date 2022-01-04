from .. import fields


def get(layer, field):
    field = fields.get(layer, field)
    if not field:
        raise Exception("Field must be supplied as common.Field, ogr.FieldDefn or a field name.")
    return field
