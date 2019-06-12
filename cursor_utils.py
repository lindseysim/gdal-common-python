
import collections
import arcpy

# Convenience methods for accessing cursor rows as dicts and tuples
# See: http://arcpy.wordpress.com/2012/07/12/getting-arcpy-da-rows-back-as-dictionaries/

# Returns rows as dicts
# example usage:
#   for row in rows_as_dicts(searchCursor):
#       print row['CITY_NAME']
def rows_as_dicts(cursor):
    colnames = cursor.fields
    for row in cursor:
        yield dict(zip(colnames, row))

# Returns rows as namedtuples
# example usage:
#   for row in rows_as_namedtuples(searchCursor):
#       print row.CITY_NAME
def rows_as_namedtuples(cursor):
    col_tuple = collections.namedtuple('Row', cursor.fields)
    for row in cursor:
        yield col_tuple(*row)

# Updates rows using UpdateCursor and rows as dicts
# example usage:
#   for row in rows_as_update_dicts(updateCursor):
#       row['CITY_NAME'] = row['CITY_NAME'].title()
def rows_as_update_dicts(cursor):
    colnames = cursor.fields
    for row in cursor:
        row_object = dict(zip(colnames, row))
        yield row_object
        cursor.updateRow([row_object[colname] for colname in colnames])
