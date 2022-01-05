import os
from ._getlayer import get as _get_layer
from .. import features
from . import reproject


def rectify(input_datasource, method_datasource, output_path, tmp_reproj_path, overwrite=False):
    input_layer, ds1 = _get_layer(input_datasource, allow_path=True)

    if not method_datasource:
        method_layer = None
        ds2 = None
        reproj_ds = None

    else:
        method_layer, ds2 = _get_layer(method_datasource, allow_path=True)

        input_srs = input_layer.GetSpatialRef()
        check_srs = method_layer.GetSpatialRef()
        reproj_ds = None
        if not input_srs.IsSame(check_srs):
            if not tmp_reproj_path:
                raise Exception("Reprojection required, supply temporary reprojection path (tmp_reproj_path)")
            if os.path.isdir(tmp_reproj_path):
                tmp_reproj_path = os.path.join(tmp_reproj_path, "tmp-reproj.shp")
            reproj_ds = reproject.features(method_layer, tmp_reproj_path, to_srs=input_srs, overwrite=overwrite)
            method_datasource = reproj_ds
            method_layer = method_datasource.GetLayer()

    input_datasource = input_datasource if not ds1 else ds1
    output_ds = None if not output_path else features.copy_datasource_as_empty(input_datasource, output_path, overwrite)

    return {
        'input_layer':     input_layer,
        'method_layer':    method_layer,
        'output_ds':       output_ds,
        'reproj_ds':       reproj_ds,
        'tmp_reproj_path': tmp_reproj_path,
        'ds1':             ds1,
        'ds2':             ds2
    }


def cleanup(process_objs, delete_tmp_files):
    if process_objs['reproj_ds'] and delete_tmp_files:
        del process_objs['method_layer']
        process_objs['reproj_ds'].Release()
        del process_objs['reproj_ds']
        driver = features.guess_driver(process_objs['tmp_reproj_path'])
        driver.DeleteDataSource(process_objs['tmp_reproj_path'])
    if process_objs['ds1']:
        process_objs['ds1'].Release()
        del process_objs['input_layer'], process_objs['ds1']
    if process_objs['ds2']:
        process_objs['ds2'].Release()
        del process_objs['method_layer'], process_objs['ds2']
