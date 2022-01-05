from osgeo import ogr
from .. import features


def get(datasource, for_write=False, allow_path=False):
    if isinstance(datasource, ogr.DataSource):
        return datasource.GetLayer(), None
    elif isinstance(datasource, ogr.Layer):
        return datasource, None
    elif allow_path and isinstance(datasource, str):
        datasource = features.get_datasource(datasource, write=for_write)
        layer = datasource.GetLayer()
        return layer, datasource
    else:
        raise Exception("Must supply ogr DataSource or Layer as input")
