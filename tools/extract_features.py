import ogr
import feature_utils


def extractFeatures(input_dataset, validation_func, output_path, overwrite=False):
    if isinstance(input_dataset, ogr.Layer):
        input_layer = input_dataset
    elif isinstance(input_dataset, ogr.DataSource):
        input_layer = input_dataset.GetLayer()
    else:
        raise Exception("Input datasets must be instance of ogr Layer or DataSource")

    output_ds = feature_utils.copyFeatureDatasetAsEmpty(input_dataset, output_path, overwrite)
    output_layer = output_ds.GetLayer()

    feature = input_layer.GetNextFeature()
    while feature:
        if validation_func(feature):
            output_layer.CreateFeature(feature)
        feature = None
        feature = input_layer.GetNextFeature()

    return output_ds
