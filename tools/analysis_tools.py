import ogr
import feature_utils
import projection_utils


def __rectifyInputs(input_dataset, method_dataset, output_path, tmp_reproj_path, overwrite=False):
    if isinstance(input_dataset, ogr.Layer):
        input_layer = input_dataset
    elif isinstance(input_dataset, ogr.DataSource):
        input_layer = input_dataset.GetLayer()
    else:
        raise Exception("Input datasets must be instance of ogr Layer or DataSource")

    if isinstance(method_dataset, ogr.Layer):
        method_layer = method_dataset
    elif isinstance(method_dataset, ogr.DataSource):
        method_layer = method_dataset.GetLayer()
    else:
        raise Exception("Input datasets must be instance of ogr Layer or DataSource")

    input_srs = input_layer.GetSpatialRef()
    check_srs = method_layer.GetSpatialRef()
    reproj_ds = None
    if not input_srs.IsSame(check_srs):
        reproj_ds = projection_utils.reprojectFeatureDataset(method_layer, tmp_reproj_path, to_srs=input_srs, overwrite=overwrite)
        method_dataset = reproj_ds
        method_layer = method_dataset.GetLayer()

    output_ds = feature_utils.copyFeatureDatasetAsEmpty(input_dataset, output_path, overwrite)

    return {
        'input_layer': input_layer,
        'method_layer': method_layer,
        'output_ds': output_ds,
        'was_reprojected': reproj_ds is not None
    }


def clip(input_dataset, clip_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, clip_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer  = process_objs['input_layer']
    clip_layer   = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()

    input_layer.Clip(clip_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds


def erase(input_dataset, erase_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, erase_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer  = process_objs['input_layer']
    erase_layer  = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()

    input_layer.Erase(erase_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds


def identity(input_dataset, identity_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, identity_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer    = process_objs['input_layer']
    identity_layer = process_objs['method_layer']
    output_ds      = process_objs['output_ds']
    output_layer   = output_ds.GetLayer()

    input_layer.Identity(identity_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds


def intersection(input_dataset, intersect_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, intersect_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer     = process_objs['input_layer']
    intersect_layer = process_objs['method_layer']
    output_ds       = process_objs['output_ds']
    output_layer    = output_ds.GetLayer()

    input_layer.Intersection(intersect_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds


def symDifference(input_dataset, diff_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, diff_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer  = process_objs['input_layer']
    diff_layer   = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()

    input_layer.SymDifference(diff_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds


def union(input_dataset, union_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, union_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer  = process_objs['input_layer']
    union_layer  = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()

    input_layer.Union(union_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds


def update(input_dataset, update_dataset, output_path, tmp_reproj_path, overwrite=False, delete_tmp_files=True):
    process_objs = __rectifyInputs(input_dataset, update_dataset, output_path, tmp_reproj_path, overwrite=overwrite)

    input_layer  = process_objs['input_layer']
    update_layer = process_objs['method_layer']
    output_ds    = process_objs['output_ds']
    output_layer = output_ds.GetLayer()

    input_layer.Update(update_layer, output_layer)

    if process_objs['was_reprojected'] and delete_tmp_files:
        driver = feature_utils.getDriver(tmp_reproj_path)
        driver.DeleteDataSource(tmp_reproj_path)

    return output_ds
