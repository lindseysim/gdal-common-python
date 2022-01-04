import os
from osgeo import ogr
from .. import features
from .. import fields as fieldutils
from ._getlayer import get as _getLayer


def singular(dataset, output_path, layer_name="dissolve", overwrite=False):
    '''
    Dissolve all features in a dataset a single polygon.
    :param dataset: (ogr.DataSource|ogr.Layer|str) The feature datasource of to dissolve, provided as ogr.DataSource,
           ogr.Layer, or filepath.
    :param output_path: (str) The output path to save the dissolved datasource at.
    :param [layer_name="dissolve"]: (str) The layer name.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return: (ogr.DataSource) The Datasource for the newly dissolved feature layer.
    '''
    layer, ds = _getLayer(dataset, allow_path=True)
    srs = layer.GetSpatialRef()
    all_geoms = []
    layer.SetNextByIndex(0)
    feat = layer.GetNextFeature()
    while feat:
        geom = feat.GetGeometryRef()
        gtype = geom.GetGeometryType()
        if gtype == ogr.wkbPolygon:
            all_geoms.append(geom.Clone())
        elif gtype == ogr.wkbMultiPolygon:
            g = 0
            gcount = geom.GetGeometryCount()
            while g < gcount:
                poly = geom.GetGeometryRef(g)
                all_geoms.append(poly.Clone())
                g += 1
            del poly
        else:
            raise Exception("Tool currently only supports polygons or multipolygons")
        feat = layer.GetNextFeature()
    layer.SetNextByIndex(0)

    del geom, feat, layer
    if ds:
        ds.Release()
        del ds

    ugeom = ogr.Geometry(ogr.wkbMultiPolygon)
    for geom in all_geoms:
        ugeom.AddGeometry(geom)
    unioned_geom = ugeom.UnionCascaded()
    if not unioned_geom:
        raise Exception("Error occurred during geometry union.")
    del geom, ugeom

    driver = features.getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)
    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(layer_name, srs, ogr.wkbMultiPolygon)
    defn = layer.GetLayerDefn()

    feat = ogr.Feature(defn)
    feat.SetGeometry(unioned_geom)
    layer.CreateFeature(feat)

    del feat, layer, unioned_geom
    return ds


def singlepart(dataset, output_path, layer_name="dissolve-singlepart", overwrite=False):
    '''
    Dissolve all features in a dataset to single-part polygons.
    :param dataset: (ogr.DataSource|ogr.Layer|str) The feature datasource of to dissolve, provided as ogr.DataSource,
           ogr.Layer, or filepath.
    :param output_path: (str) The output path to save the dissolved datasource at.
    :param [layer_name="dissolve-singelpart"]: (str) The layer name.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return: (ogr.DataSource) The Datasource for the newly dissolved feature layer.
    '''
    layer, ds = _getLayer(dataset, allow_path=True)
    srs = layer.GetSpatialRef()
    all_geoms = []
    layer.SetNextByIndex(0)
    feat = layer.GetNextFeature()
    while feat:
        geom = feat.GetGeometryRef()
        gtype = geom.GetGeometryType()
        if gtype == ogr.wkbPolygon:
            all_geoms.append(geom.Clone())
        elif gtype == ogr.wkbMultiPolygon:
            g = 0
            gcount = geom.GetGeometryCount()
            while g < gcount:
                poly = geom.GetGeometryRef(g)
                all_geoms.append(poly.Clone())
                g += 1
        else:
            raise Exception("Tool currently only supports polygons or multipolygons")
        feat = layer.GetNextFeature()
    layer.SetNextByIndex(0)

    del geom, feat, layer
    if ds:
        ds.Release()
        del ds

    unioned_geoms = []
    gids_processed = []

    num_geoms = len(all_geoms)
    i = -1
    while True:
        i += 1
        if i == num_geoms:
            break
        if i in gids_processed:
            continue
        group = [all_geoms[i]]
        gids_processed.append(i)
        j = i
        while True:
            j += 1
            if j >= num_geoms:
                break
            if j in gids_processed:
                continue
            for geom in group:
                if all_geoms[j].Intersects(geom):
                    group.append(all_geoms[j])
                    gids_processed.append(j)
                    j = i
                    break

        ugeom = ogr.Geometry(ogr.wkbMultiPolygon)
        for geom in group:
            ugeom.AddGeometry(geom)
        unioned_geom = ugeom.UnionCascaded() if len(group) > 1 else ugeom
        unioned_geoms.append([unioned_geom, len(group)])

        del geom, ugeom, unioned_geom, group

    del all_geoms, gids_processed

    driver = features.getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)
    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(layer_name, srs, ogr.wkbMultiPolygon)
    count_field = fieldutils.create(layer, "FEAT_COUNT", int)
    defn = layer.GetLayerDefn()

    for geom_and_count in unioned_geoms:
        feat = ogr.Feature(defn)
        feat.SetGeometry(geom_and_count[0])
        fieldutils.setValue(feat, count_field, geom_and_count[1])
        layer.CreateFeature(feat)

    del count_field, feat, layer, unioned_geoms
    return ds


def onField(dataset, output_path, on_fields, singlepart=False, layer_name="dissolve-onfield", overwrite=False):
    '''
    Dissolve all features in a dataset by a field or fields.
    :param dataset: (ogr.DataSource|ogr.Layer|str) The feature datasource to dissolve, provided as ogr.DataSource,
           ogr.Layer, or filepath.
    :param output_path: (str) The output path to save the dissolved datasource at.
    :param on_field: (common.Field[]|ogr.FieldDefn[]|str[]) The field or fields to dissolve on such that each feature
           will represent a unique combination of these fields. May be provided as list containing instances of Field,
           ogr.FieldDefn, or the field name.
    :param [singlepart=False]: (boolean) If true, breaks features on continguous geometries. Otherwise multipart
           geometries are allowed per feature.
    :param [layer_name="dissolve-onfield"]: (str) The layer name.
    :param [overwrite=False]: (boolean) If False, throws exception is output path already exists. Otherwise overwrites
           silently.
    :return: (ogr.DataSource) The Datasource for the newly dissolved feature layer.
    '''
    layer, ds = _getLayer(dataset, allow_path=True)
    srs = layer.GetSpatialRef()
    if not isinstance(on_fields, list):
        on_fields = [on_fields]
    fields = [fieldutils.get(layer, f) for f in on_fields]
    if None in fields:
        raise Exception("One of more fields provided do not exist in dataset.")

    unique_sets = []    
    feature_groups = []

    f = -1
    layer.SetNextByIndex(0)
    feat = layer.GetNextFeature()
    while feat:
        f += 1
        values = [fieldutils.value(feat, field) for field in fields]

        matched = -1
        for i in range((len(unique_sets))):
            match = True
            for k in range(len(fields)):
                if values[k] != unique_sets[i][k]:
                    match = False
                    break
            if match:
                matched = i
                break

        if matched < 0:
            unique_sets.append(values)
            feature_groups.append([f])
        else:
            feature_groups[matched].append(f)

        feat = layer.GetNextFeature()
    layer.SetNextByIndex(0)

    unioned_geoms = []

    for g in range(len(feature_groups)):
        geom_group = []
        for f in feature_groups[g]:
            feat = layer.GetFeature(f)
            geom = feat.GetGeometryRef()
            gtype = geom.GetGeometryType()
            if gtype == ogr.wkbPolygon:
                geom_group.append(geom.Clone())
            elif gtype == ogr.wkbMultiPolygon:
                for p in range(geom.GetGeometryCount()):
                    poly = geom.GetGeometryRef(p)
                    geom_group.append(poly.Clone())
                del poly
            else:
                raise Exception("Tool currently only supports polygons or multipolygons")
        del geom, feat

        if not singlepart:
            groups = [geom_group]
        else:
            groups = []
            num_geoms = len(geom_group)
            gids_processed = []
            i = -1
            while True:
                i += 1
                if i == num_geoms:
                    break
                if i in gids_processed:
                    continue
                capture_group = [geom_group[i]]
                gids_processed.append(i)
                j = i
                while True:
                    j += 1
                    if j >= num_geoms:
                        break
                    if j in gids_processed:
                        continue
                    for geom in capture_group:
                        if geom_group[j].Intersects(geom):
                            capture_group.append(geom_group[j])
                            gids_processed.append(j)
                            j = i
                            break
                groups.append(capture_group)
            del gids_processed, geom_group, capture_group

        for group in groups:
            ugeom = ogr.Geometry(ogr.wkbMultiPolygon)
            for geom in group:
                ugeom.AddGeometry(geom)
            unioned_geom = ugeom.UnionCascaded() if len(group) > 1 else ugeom
            unioned_geoms.append([unioned_geom, g, len(group)])
        del geom, group, groups

    if ds:
        ds.Release()
        del layer, ds

    driver = features.getFeatureDriver(output_path)
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("{0} already exists (to overwrite, set overwrite=True)".format(output_path))
        driver.DeleteDataSource(output_path)
    ds = driver.CreateDataSource(output_path)
    layer = ds.CreateLayer(layer_name, srs, ogr.wkbMultiPolygon)
    count_field = fieldutils.create(layer, "FEAT_COUNT", int)
    defn = layer.GetLayerDefn()

    for f in fields:
        layer.CreateField(f.defn)

    for ugeom, igroup, num_union in unioned_geoms:
        feat = ogr.Feature(defn)
        feat.SetGeometry(ugeom)
        for i in range(len(fields)):
            fieldutils.setValue(feat, fields[i], unique_sets[igroup][i])
        fieldutils.setValue(feat, count_field, num_union)
        layer.CreateFeature(feat)

    del driver, defn, layer
    return ds
