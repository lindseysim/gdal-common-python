import ogr


def toGeoJson(feature_dataset):
    if isinstance(feature_dataset, ogr.DataSource):
        feat_layer = feature_dataset.GetLayer()
    elif isinstance(feature_dataset, ogr.Layer):
        feat_layer = feature_dataset
    else:
        raise Exception("Must supply ogr DataSource or Layer as input")

    geojson = (
        '{\n' +
        '  "type": "FeatureCollection", \n' +
        '  "features": [\n'
    )
    first = True
    for feature in feat_layer:
        if first:
            first = False
        else:
            geojson += ",\n"
        geojson += "    " + feature.ExportToJson()
    geojson += "\n  ]\n}"
    return geojson
