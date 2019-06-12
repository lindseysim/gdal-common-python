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


#-----------------------------------------------------------------------------------------------------------------------
# Return flipped line by reversing vertex array.
def flipLine(polyline):
    pts = polyline.getPart(0)
    flippedPts = arcpy.Array([pts.getObject(i) for i in range(pts.count)[::-1]])
    return arcpy.Polyline(flippedPts)


#-----------------------------------------------------------------------------------------------------------------------
# see http://gis.stackexchange.com/questions/16764/how-to-determine-on-which-side-of-a-line-a-polygon-feature-falls

class OrientationType:
    Left, Right, Coincident, Unknown = range(4)


# Determines if a point is oriented left, right, or coincident with a directed line
def getPointOrientation(pointX, pointY, lineStartX, lineStartY, lineEndX, lineEndY):

    result = OrientationType.Unknown

    Ax = lineStartX
    Ay = lineStartY
    Bx = lineEndX
    By = lineEndY
    Px = pointX
    Py = pointY

    dotV = ((Ay - By) * (Px - Ax)) + ((Bx - Ax) * (Py - Ay))

    if dotV < 0:
        result = OrientationType.Right  # opposite direction to normal vector
    elif dotV > 0:
        result = OrientationType.Left
    elif dotV == 0:
        result = OrientationType.Coincident

    return result


#-----------------------------------------------------------------------------------------------------------------------
# Create feature class of transects based on line features.
#   lineFeatures: source line feature class
#   lineIdField: line identifier field
#   transIdField: transect identifier field
#   transLengthField (optional): field to use for transect length
#   outName (optional): output feature class name
#   transPts (optional): point feature class to use for transect intersects
#   transLength (optional): length of transect on each side of line
#   transSegLength (optional): total length of line segment used to orient transects perpendicularly to line
#   includeFields (optional): fields to retain in output feature class
#   downstreamOrientation (optional): if True, transect point order will be enforced from left to right facing downstream
def buildTransects(lineFeatures, lineIdField, transIdField, transLengthField=None, outName='transects',
                   transPts=None, transLength=20, transSegLength=10, includeFields=[],
                   downstreamOrientation=False):
    import cursor_utils

    sr = arcpy.Describe(lineFeatures).spatialReference
    if arcpy.Exists(outName):
        arcpy.Delete_management(outName)
    transects = arcpy.CreateFeatureclass_management(arcpy.env.workspace, outName, "POLYLINE", spatial_reference=sr)

    lineSlopeField = "line_slope"
    arcpy.AddField_management(transects, lineSlopeField, 'DOUBLE')
    arcpy.AddField_management(transects, lineIdField, 'LONG')

    for name in includeFields:
        if transPts:
            field = [f for f in arcpy.ListFields(transPts) if f.name == name][0]
        else:
            field = [f for f in arcpy.ListFields(lineFeatures) if f.name == name][0]
        if field:
            arcpy.AddField_management(transects, name, field.type)

    counter = 0

    geomDict = {}

    if not transPts:
        # if transect points not provided, create transect at midpoint of each line feature
        with arcpy.da.SearchCursor(lineFeatures, ["SHAPE@", lineIdField, transLengthField] + includeFields) as cursor:
            for row in cursor_utils.rows_as_dicts(cursor):

                # Create the geometry object
                line = row["SHAPE@"]

                # Get coordinate values as lists
                firstpoint = line.firstPoint
                lastpoint = line.lastPoint
                midpoint = line.positionAlongLine(0.50, True).firstPoint

                transLength = transLength or row[transLengthField]
                lineId = row[lineIdField]

                transVals = makeTransect(firstpoint, lastpoint, midpoint, transLength)

                polyline = transVals["polyline"]
                m = transVals["m"]

                # enforce orientation of transect from left to right looking downstream
                if downstreamOrientation:
                    transectStartPt = polyline.firstPoint
                    if getPointOrientation(transectStartPt.X, transectStartPt.Y, line.firstPoint.X, line.firstPoint.Y, line.lastPoint.X, line.lastPointY) != OrientationType.Left:
                        # flip transect
                        polyline = flipLine(polyline)


                geomDict[counter] = [polyline, m, lineId] + [row[f] for f in includeFields]

                counter += 1

        with arcpy.da.InsertCursor(transects, ["SHAPE@", lineSlopeField, lineIdField] + includeFields) as icursor:
            for key, row in geomDict.iteritems():
                icursor.insertRow(row)

    else:  # if transPts

        # add transIdField to transects if necessary
        if transIdField not in set([f.name for f in arcpy.ListFields(transects)]):
            idField = [f for f in arcpy.ListFields(transPts) if f.name == transIdField][0]
            arcpy.AddField_management(transects, transIdField, idField.type)

        linesLyr = arcpy.MakeFeatureLayer_management(lineFeatures, "linesLyr")
        transPtsLyr = arcpy.MakeFeatureLayer_management(transPts, "transPtsLyr")

        lineIds = sorted(set([row[0] for row in arcpy.da.SearchCursor(linesLyr, [lineIdField])]))
        for lineId in lineIds:
            # select intersecting line
            # assumes transect points are snapped to a line
            arcpy.SelectLayerByAttribute_management(linesLyr, "NEW_SELECTION", '"{0}" = {1}'.format(lineIdField, lineId))
            arcpy.SelectLayerByLocation_management(transPtsLyr, "INTERSECT", linesLyr, selection_type="NEW_SELECTION")

            if int(arcpy.GetCount_management(transPtsLyr).getOutput(0)) > 0:
                if not transLength:
                    line, length = [(row[0], row[1]) for row in arcpy.da.SearchCursor(linesLyr, ["SHAPE@", transLengthField])][0]
                else:
                    line = [row[0] for row in arcpy.da.SearchCursor(linesLyr, ["SHAPE@"])][0]
                    length = transLength

                geomDict = {}

                with arcpy.da.SearchCursor(transPtsLyr, ["SHAPE@", transIdField, lineIdField] + includeFields) as cursor:
                    for row in cursor_utils.rows_as_dicts(cursor):
                        midpoint = row["SHAPE@"].firstPoint
                        # get distance from start point of line to transect pt
                        ptDist = line.measureOnLine(midpoint)
                        # calculate upstream/downstream points for segment
                        # these points are used to orient the transect perpendicularly to the line
                        firstpoint = line.positionAlongLine(ptDist - transSegLength / 2).firstPoint
                        lastpoint = line.positionAlongLine(ptDist + transSegLength / 2).firstPoint

                        transVals = makeTransect(firstpoint, lastpoint, midpoint, length)

                        polyline = transVals["polyline"]
                        m = transVals["m"]

                        # enforce orientation of transect from left to right looking downstream
                        if downstreamOrientation:
                            transectStartPt = polyline.firstPoint
                            if getPointOrientation(transectStartPt.X, transectStartPt.Y, line.firstPoint.X, line.firstPoint.Y, line.lastPoint.X, line.lastPoint.Y) != OrientationType.Left:
                                # flip transect
                                polyline = flipLine(polyline)

                        geomDict[counter] = [polyline, m, row[transIdField], row[lineIdField]] + [row[f] for f in includeFields]

                        counter += 1

                with arcpy.da.InsertCursor(transects, ["SHAPE@", lineSlopeField, transIdField, lineIdField] + includeFields) as icursor:
                    for key, row in geomDict.iteritems():
                        icursor.insertRow(row)

    return transects


#-----------------------------------------------------------------------------------------------------------------------
# Create transect line centered at midpoint and oriented perpindicularly to segment defined by (firstpoint, lastpoint).
def makeTransect(firstpoint, lastpoint, midpoint, transLength):
    # Get X and Y values for each point
    startx = firstpoint.X
    starty = firstpoint.Y
    endx = lastpoint.X
    endy = lastpoint.Y
    midx = midpoint.X
    midy = midpoint.Y

    linePts, m = orientTransect(midx, midy, transLength, startx, starty, endx, endy)

    returnVals = {"polyline": arcpy.Polyline(linePts), "m": m}

    return returnVals


#-----------------------------------------------------------------------------------------------------------------------
# see http://gis.stackexchange.com/questions/20855/arcgis10-create-perpendicular-transects-to-stream-at-specified-intervals
# and http://arcscripts.esri.com/details.asp?dbid=15756

# Define transect orientation.
def orientTransect(mid_x, mid_y, transLength, start_x, start_y, end_x, end_y):

    # If the line is horizontal or vertical, the slope and
    # negative reciprocal calculations will fail, so do this instead
    if start_y == end_y or start_x == end_x:
        # horizontal
        if start_y == end_y:
            y1 = mid_y + transLength
            y2 = mid_y - transLength
            x1 = mid_x
            x2 = mid_x
        # vertical
        if start_x == end_x:
            y1 = mid_y
            y2 = mid_y
            x1 = mid_x + transLength
            x2 = mid_x - transLength
    else:
        delta_x = start_x - end_x
        delta_y = start_y - end_y

        # Get slope of line
        # NOTE: "slope" here refers to 2D slope, not 3D slope
        m = (delta_y/delta_x)

        # Get negative reciprocal
        negativereciprocal = -1*(delta_x/delta_y)

        # For all values of slope, calculate perpendicular line
        # with length = transLength
        if m > 0:
            if m >= 1:
                y1 = negativereciprocal*(transLength) + mid_y
                y2 = negativereciprocal*(-transLength) + mid_y
                x1 = mid_x + transLength
                x2 = mid_x - transLength
            if m < 1:
                y1 = mid_y + transLength
                y2 = mid_y - transLength
                x1 = (transLength/negativereciprocal) + mid_x
                x2 = (-transLength/negativereciprocal) + mid_x

        if m < 0:
            if m >= -1:
                y1 = mid_y + transLength
                y2 = mid_y - transLength
                x1 = (transLength/negativereciprocal) + mid_x
                x2 = (-transLength/negativereciprocal) + mid_x

            if m < -1:
                y1 = negativereciprocal*(transLength) + mid_y
                y2 = negativereciprocal*(-transLength) + mid_y
                x1 = mid_x + transLength
                x2 = mid_x - transLength

    transPts = arcpy.Array()
    transPts.add(arcpy.Point(x1, y1))
    transPts.add(arcpy.Point(x2, y2))

    return transPts, m