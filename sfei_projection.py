# Copyright 2014 San Francisco Estuary Institute.

# This file is part of the SFEI toolset.
#
# The SFEI toolset is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The SFEI toolset is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the SFEI toolset.  If not, see http://www.gnu.org/licenses/.


import arcpy
import os


NAD_1983_California_Teale_Albers = arcpy.SpatialReference(3310)
WGS_1984_Web_Mercator_Auxiliary_Sphere = arcpy.SpatialReference(3857)


#-----------------------------------------------------------------------------------------------------------------------
# Project feature class to spatial reference. Default spatial reference is NAD_1983_California_Teale_Albers.
#   fc: source feature class
#   sr (optional): destination arcpy.SpatialReference object
#   replaceFc (optional): flag indicating whether projection should be done in place
#   extent (optional): arcpy.Extent object to use for identifying valid transformations
def projectToSR(fc, sr=NAD_1983_California_Teale_Albers, replaceFc=True, extent=None):
    from sfei_utils import replace
    source = fc
    fcSr = arcpy.Describe(fc).spatialReference
    if fcSr.factoryCode != sr.factoryCode:
        name, ext = os.path.splitext(os.path.basename(source))
        dest = os.path.join(os.path.dirname(source), "{0}_{1}{2}".format(name, str(sr.factoryCode), ext))
        transformations = arcpy.ListTransformations(from_sr=fcSr, to_sr=sr, extent=extent)
        transform = transformations[0] if len(transformations) else None
        arcpy.Project_management(source, dest, sr, transform_method=transform)
        if replaceFc:
            replace(source, dest)
            return source
        return dest
    else:
        return source


#-----------------------------------------------------------------------------------------------------------------------
# Project raster to spatial reference. Default spatial reference is NAD_1983_California_Teale_Albers.
#   raster: source raster
#   sr (optional): destination arcpy.SpatialReference object
#   replaceRaster (optional): flag indicating whether projection should be done in place
#   extent (optional): arcpy.Extent object to use for identifying valid transformations
#   resampling_type (optional): resampling method to use in projection
def projectRasterToSR(raster, sr=NAD_1983_California_Teale_Albers, replaceRaster=True, extent=None, resampling_type="BILINEAR"):
    from sfei_utils import replace
    source = raster
    sourceRas = arcpy.Raster(raster)
    sourceSr = arcpy.Describe(sourceRas).spatialReference
    if sourceSr.factoryCode != sr.factoryCode:
        name, ext = os.path.splitext(os.path.basename(source))
        dest = os.path.join(os.path.dirname(source), "{0}_{1}{2}".format(name, str(sr.factoryCode), ext))
        transformations = arcpy.ListTransformations(from_sr=sourceSr, to_sr=sr, extent=extent)
        transform = transformations[0] if len(transformations) else None
        arcpy.ProjectRaster_management(sourceRas, dest, sr, geographic_transform=transform, resampling_type=resampling_type)
        if replaceRaster:
            replace(source, dest)
            return source
        return dest
    else:
        return source


#-----------------------------------------------------------------------------------------------------------------------
# Helper to project and clip feature class in one method.
#   fc: source feature class
#   sr (optional): destination arcpy.SpatialReference object--if None, no projection will be done
#   extent (optional): arcpy.Extent object to use for identifying valid transformations
#   clipTo (optional): arcpy.Extent object to use for clipping--if None, no clippping will be done
def projectAndClip(fc, sr=None, extent=None, clipTo=None):
    from sfei_utils import replace
    if sr:
        fc = projectToSR(fc, sr, extent=extent)
    if clipTo:
        clipOutput = os.path.join(os.path.dirname(fc), arcpy.Describe(fc).name + "_clip")
        arcpy.Clip_analysis(fc, clipTo, clipOutput)
        replace(fc, clipOutput)

