# Copyright 2014 San Francisco Estuary Institute.

# This file is part of RipZET.
#
# RipZET is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RipZET is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RipZET.  If not, see http://www.gnu.org/licenses/.


import arcpy
import sys
import os
import time
import datetime
from bisect import bisect_left
import math

from arcpy import env
from arcpy.sa import *

from sfei_time import timeStamp
from sfei_time import formatTime



ALL_MESSAGES = []

# messages to add to summary log
LOG_MESSAGES = []

TIMESTAMP_MESSAGES = False

INFORMATION = 0
WARNING = 1
ERROR = 2
MESSAGE_STRINGS = ["", "WARNING", "ERROR"]

#-----------------------------------------------------------------------------------------------------------------------
# Clear global message lists. Because they are globals, they persist in memory between tool runs unless ArcMap/ArcCatalog is closed.
# NOTE: Call this at the start of tool execution.
def initMsgs():
    global ALL_MESSAGES, LOG_MESSAGES
    ALL_MESSAGES = []
    LOG_MESSAGES = []

#-----------------------------------------------------------------------------------------------------------------------
# Handle message output with options.
#   message: message string
#   msgType (optional): INFORMATION, WARNING, or ERROR
#   logIt (optional): append message to LOG_MESSAGES list
#   displayMsg (optional): add message to ArcGIS output
def printMsg(message, msgType=INFORMATION, module='', logIt=False, displayMsg=True):
    messageStr = str(message)
    prefix = ""
    if TIMESTAMP_MESSAGES:
        prefix = '[{0}] '.format(timeStamp(time.localtime()))
    if module:
        prefix += '[{0}] '.format(module)
    if displayMsg:
        if msgType == WARNING:
            arcpy.AddWarning(prefix + messageStr)
        elif msgType == ERROR:
            arcpy.AddError(prefix + messageStr)
        else:
            arcpy.AddMessage(prefix + messageStr)
    if logIt or msgType in [WARNING, ERROR]:
        if msgType in [WARNING, ERROR]:
            if TIMESTAMP_MESSAGES:
                endOfTime = prefix.find("]")
                prefix = "{0} {1}: {2}".format(prefix[:endOfTime+1], MESSAGE_STRINGS[msgType], prefix[endOfTime+1:])
            else:
                prefix = "{0}: {1}".format(MESSAGE_STRINGS[msgType], prefix)
        LOG_MESSAGES.append(prefix + messageStr)
    ALL_MESSAGES.append(prefix + messageStr)


#-----------------------------------------------------------------------------------------------------------------------
# Write ALL_MESSAGES list to text file.
def writeMessages(txtPath, append=True):
    if append:
        mode = "a+"
    else:
        mode = "w"
    with open(txtPath, mode) as txtfile:
        for m in ALL_MESSAGES:
            txtfile.write(str(m) + '\n')


#-----------------------------------------------------------------------------------------------------------------------
# Print environment settings.
# see http://resources.arcgis.com/en/help/main/10.2/index.html#//03q300000077000000
def dumpEnvironmentSettings():
    environments = arcpy.ListEnvironments()
    environments.sort()
    printMsg("")
    printMsg("-----------------------------------------------------------------------------------------------------------------------")
    printMsg("ENVIRONMENT SETTINGS")
    for environment in environments:
        printMsg("{0:<30}: {1}".format(environment, arcpy.env[environment]))
    printMsg("-----------------------------------------------------------------------------------------------------------------------")
    printMsg("")


#-----------------------------------------------------------------------------------------------------------------------
# Return string consisting of textString with spaces filled.
#   textString: source string
#   replaceWith (optional): character to replace spaces
def fillSpaces(textString, replaceWith='_'):
    return textString.replace(' ', replaceWith)


#-----------------------------------------------------------------------------------------------------------------------
# Replace data source in place by deleting old data and renaming new data to old data.
#   pathToOld: old data that will be replaced
#   pathToNew: new data that will replace old data
def replace(pathToOld, pathToNew):
    if arcpy.Exists(pathToNew):
        arcpy.Delete_management(pathToOld)
        arcpy.Rename_management(pathToNew, pathToOld)


#-----------------------------------------------------------------------------------------------------------------------
# Determine whether a given object can be parsed as a numeric type.
def isNumber(obj):
    try:
        float(obj)
    except:
        return False
    return True


#-----------------------------------------------------------------------------------------------------------------------
# Parse value as float.
def tryParseFloat(val):
    floatVal = 0.0
    try:
        floatVal = float(val)
    except:
        printMsg("WARNING: '" + str(val) + "' could not be parsed as float")
        pass
    return floatVal


#-----------------------------------------------------------------------------------------------------------------------
# Return arcpy.env.cellSize as a float instead of a string.
def getCellSizeFloat():
    return tryParseFloat(env.cellSize)


#-----------------------------------------------------------------------------------------------------------------------
# Create a backup copy of input with unique name.
def backup(input, workspace=None):
    if arcpy.Exists(input):
        backup = createUniqueName(input, workspace)
        arcpy.Rename_management(input, backup)


#-----------------------------------------------------------------------------------------------------------------------
# Create a unique name for input in workspace.
def createUniqueName(input, workspace=None):
    if not workspace:
        workspace = os.path.dirname(input) or None
    return arcpy.CreateUniqueName(os.path.basename(input), workspace)


#-----------------------------------------------------------------------------------------------------------------------
# Return a unique file name: if fileName is already unique, return fileName.
def getUniqueFileName(fileName):
    baseName, ext = os.path.splitext(fileName)
    i = 1
    while os.path.exists(fileName):
        fileName = "{0}_{1}{2}".format(baseName, str(i), ext)
        i += 1
    return fileName


#-----------------------------------------------------------------------------------------------------------------------
# Return a unique field name for a feature class: if fieldName is already unique, return fieldName.
def getUniqueFieldName(fieldName, fc):
    fieldNames = [k.name for k in arcpy.ListFields(fc)]
    baseName = fieldName
    i = 1
    while fieldName in fieldNames:
        fieldName = "{0}_{1}".format(baseName, str(i))
        i += 1
    return fieldName


#-----------------------------------------------------------------------------------------------------------------------
# Return a sorted list of unique field values.
def getUniqueFieldValues(fc, field):
    values = [row[0] for row in arcpy.da.SearchCursor(fc, (field))]
    uniqueValues = sorted(set(values))
    return uniqueValues


#-----------------------------------------------------------------------------------------------------------------------
# Format number with places.
def formatNumber(val, places=2):
    numericFormat = '{:.' + str(places) + 'f}'
    return numericFormat.format(val)


#-----------------------------------------------------------------------------------------------------------------------
# Return dict of valueField values keyed by keyField value.
def getFieldValueDict(fc, keyField, valueField):
    return {row[0]: row[1] for row in arcpy.da.SearchCursor(fc, [keyField, valueField])}


#-----------------------------------------------------------------------------------------------------------------------
# Return median value.
def median(valueList):
    sortedValues = sorted(valueList)
    length = len(sortedValues)
    if not length % 2:
        return (sortedValues[length / 2] + sortedValues[length / 2 - 1]) / 2.0
    return sortedValues[length / 2]


#-----------------------------------------------------------------------------------------------------------------------
# Get int count of features in feature class.
def getCount(fc):
    return int(arcpy.GetCount_management(fc).getOutput(0))


#-----------------------------------------------------------------------------------------------------------------------
# Calculate field stat.
def getFieldValStat(fc, field, stat):
    vals = []

    with arcpy.da.SearchCursor(fc, (field)) as cursor:
        for row in cursor:
            vals.append(row[0])

    if stat == 'max':
        return max(vals)
    elif stat == 'min':
        return min(vals)
    elif stat == 'mean':
        return float(sum(vals) / len(vals))
    elif stat == 'sum':
        return sum(vals)
    else:
        printMsg("Invalid stat type: {0}. Use 'max', 'min', 'mean', or 'sum'.".format(stat), msgType=WARNING)


#-----------------------------------------------------------------------------------------------------------------------
# Delete features with field value == 0.
def deleteZeroes(fc, field):
    lyr = arcpy.MakeFeatureLayer_management(fc)
    arcpy.SelectLayerByAttribute_management(lyr, 'NEW_SELECTION', '"' + field + '"=0')
    if getCount(lyr) > 0:
        arcpy.DeleteRows_management(lyr)
    arcpy.Delete_management(lyr)


#-----------------------------------------------------------------------------------------------------------------------
# "Fast" join.
def fastJoin(fc, fcField, joinFC, joinFCField, fields, fieldsNewNames=None):
    # Create joinList, which is a list of [name, type] for input fields
    listfields = arcpy.ListFields(joinFC)
    joinList = [[k.name, k.type] for k in listfields if k.name in fields]

    if fieldsNewNames:
        # Replace original names with new names in joinList and append old ones to list
        for name, typ in joinList:
            i = fields.index(name)
            joinList[joinList.index([name, typ])][0] = fieldsNewNames[i]
    else:
        fieldsNewNames = fields

    # As Field object types and AddField types have different names (shrug),
    # map object types to AddField types
    for name, typ in joinList:
        i = joinList.index([name, typ])
        if typ == 'Integer':
            joinList[i] = [name, 'LONG']
        elif typ == 'SmallInteger':
            joinList[i] = [name, 'SHORT']
        elif typ == 'String':
            joinList[i] = [name, 'TEXT']
        elif typ == 'Single':
            joinList[i] = [name, 'FLOAT']
        elif typ == 'Double':
            joinList[i] = [name, 'DOUBLE']

    # Add fields with associated names
    for name, typ in joinList:
        arcpy.AddField_management(fc, name, typ)

    joinDict = {}
    for f in fields:
        joinDict[f] = {}

    sFields = (joinFCField, ) + fields
    with arcpy.da.SearchCursor(joinFC, sFields) as cursor:
        for row in cursor:
            for f in fields:
                joinDict[f][row[0]] = row[fields.index(f) + 1]

    uFields = (fcField, ) + fieldsNewNames
    with arcpy.da.UpdateCursor(fc, uFields) as cursor:
        for row in cursor:
            for f in fields:
                row[fields.index(f) + 1] = joinDict[f].get(row[0], None)
            cursor.updateRow(row)


#-----------------------------------------------------------------------------------------------------------------------
# "Fast" join all.
def fastJoinAll(inFC, inField, joinFC, joinField, outName):
    """This function joins all fields permanently much faster than JoinField"""
    env.qualifiedFieldNames = False
    # Get list of field objects
    listfields = arcpy.ListFields(joinFC)
    # Get names of inFC
    desc = arcpy.Describe(inFC)
    # Make layer of inFC
    inLyr = arcpy.MakeFeatureLayer_management(inFC, 'inFC')
    # Add join and save to new fc
    arcpy.AddJoin_management(inLyr, inField, joinFC, joinField)
    joined = arcpy.CopyFeatures_management(inLyr, outName)
    # Delete original inFC and rename product to match it
    arcpy.Delete_management(inLyr)
    listFieldsOut = arcpy.ListFields(joined)
    # Delete repeat fields
    delFields = []
    for f in [k.name for k in listFieldsOut if k.name[-2:] == '_1']:
        delFields.append(f)
    arcpy.DeleteField_management(joined, delFields)
    env.qualifiedFieldNames = True
    return joined


#-----------------------------------------------------------------------------------------------------------------------
# "Fast" identity.
# see http://forums.arcgis.com/threads/100793-TIP-Simple-code-to-make-IDENTITY-or-ERASE-or-Other-Overlay-Functions-much-faster
def fastIdentity(inFL, idFL, outFC):  # Input must be Feature Layers
    arcpy.SelectLayerByLocation_management(inFL, 'INTERSECT', idFL)
    arcpy.SelectLayerByLocation_management(idFL, 'INTERSECT', inFL)
    identityOutput = "in_memory/fastIdentityOutput"
    identityOutputLyr = "fastIdentityOutputLyr"
    arcpy.Identity_analysis(inFL, idFL, identityOutput)
    arcpy.MakeFeatureLayer_management(identityOutput, identityOutputLyr)
    arcpy.MultipartToSinglepart_management(identityOutputLyr, outFC)
    arcpy.Delete_management(identityOutput)
    arcpy.Delete_management(identityOutputLyr)
    arcpy.SelectLayerByAttribute_management(inFL, "SWITCH_SELECTION")
    arcpy.Append_management(inFL, outFC, "NO_TEST","","")


#-----------------------------------------------------------------------------------------------------------------------
# "Fast" erase.
# see http://forums.arcgis.com/threads/100793-TIP-Simple-code-to-make-IDENTITY-or-ERASE-or-Other-Overlay-Functions-much-faster
# basic idea:
#   select inFL features by location (intersect with eraseFL)
#   erase eraseFL from selected inFL features
#   switch inFL selection (features that don't intersect with eraseFL)
#   merge selected inFL features and erase output as outFC
def fastErase(inFL, eraseFL, outFC):  # Input must be Feature Layers
    fastEraseClock = time.clock()
    inFLName = arcpy.Describe(inFL).name
    eraseFLName = arcpy.Describe(eraseFL).name
    printMsg("fastErase(" + inFLName + ", " + eraseFLName + ", " + outFC + ")")
    arcpy.SelectLayerByLocation_management(inFL, 'INTERSECT', eraseFL, selection_type='SUBSET_SELECTION')
    eraseOutput = "in_memory/fastEraseOutput"
    eraseOutputLyr = "fastEraseOutputLyr"
    arcpy.Erase_analysis(inFL, eraseFL, eraseOutput)
    arcpy.MakeFeatureLayer_management(eraseOutput, eraseOutputLyr)
    arcpy.SelectLayerByAttribute_management(inFL, "SWITCH_SELECTION")
    arcpy.Merge_management([inFL, eraseOutputLyr], outFC)
    if arcpy.Exists(eraseOutput):
        arcpy.Delete_management(eraseOutput)
    if arcpy.Exists(eraseOutputLyr):
        arcpy.Delete_management(eraseOutputLyr)
    printMsg("  execution time: " + formatTime(fastEraseClock))


#-----------------------------------------------------------------------------------------------------------------------
# Add field if it doesn't already exist.
def safeAddField(fc, fieldName, fieldType):
    if not fieldName in [f.name for f in arcpy.ListFields(fc)]:
        arcpy.AddField_management(fc, fieldName, fieldType)
    else:
        printMsg("Field '{0}' was not added to {1} because it already exists".format(fieldName, arcpy.Describe(fc).name), displayMsg=False)


#-----------------------------------------------------------------------------------------------------------------------
# Delete fields if they exist and can be deleted.
def safeDeleteFields(table, deleteFields = [], keepFields=[]):
    if not len(deleteFields):
        deleteFields = [f.name for f in arcpy.ListFields(table) if not f.required and f.name not in keepFields]
    for f in deleteFields:
        try:
            arcpy.DeleteField_management(table, f)
        except Exception as e:
            printMsg(str(e), msgType=WARNING)
            printMsg("Error deleting field '{0}' from table '{1}'".format(f, arcpy.Describe(table).name), msgType=WARNING)
            pass


#-----------------------------------------------------------------------------------------------------------------------
# Return list of values that occur more than once.
def getRepeats(fc, field):
    allValues = set()
    repeat = set()

    with arcpy.da.SearchCursor(fc, (field)) as cursor:
        for row in cursor:
            val = row[0]
            if val in allValues:
                repeat.add(val)
            allValues.add(val)

    return list(repeat)


#-----------------------------------------------------------------------------------------------------------------------
# Create arcpy.Parameter from options. Helper to reduce code clutter in arcpy tool initialization.
# adapted from http://joelmccune.com/2013/03/18/lessons-learned-and-ideas-for-python-toolbox-coding/
def parameter(displayName, name, datatype, parameterType=None, direction=None, multiValue=False, defaultValue=None, enabled=None):
    '''
    The parameter implementation makes it a little difficult to
    quickly create parameters with defaults. This method
    prepopulates some of these values to make life easier while
    also allowing setting a default vallue.
    '''
    # create parameter with a few default properties
    param = arcpy.Parameter(
        displayName = displayName,
        name = name,
        datatype = datatype,
        parameterType = parameterType or 'Required',
        direction = direction or 'Input',
        multiValue = multiValue,
        enabled = enabled)

    # set new parameter to a default value
    param.value = defaultValue

    # return complete parameter object
    return param


#-----------------------------------------------------------------------------------------------------------------------
# Return item by "name" attribute value.
def itemByName(items, name):
    return itemByAttrValue(items, "name", name)


#-----------------------------------------------------------------------------------------------------------------------
# Return item by attribute value.
def itemByAttrValue(items, attr, value):
    try:
        item = [i for i in items if getattr(i, attr, None) == value]
        return item[0] if item else None
    except AttributeError:
        sys.exc_clear()


#-----------------------------------------------------------------------------------------------------------------------
# Execute RepairGeometry_management in a loop until no errors remain.
#   fc: feature class to repair
#   maxIterations (optional): maximum number of repair loops (some errors may remain)
def repairGeometry(fc, maxIterations=5):
    printMsg("repairing geometry...")
    loopCount = 1
    errorsFound = True
    try:
        while errorsFound and loopCount <= maxIterations:
            printMsg("  pass " + str(loopCount))
            res = arcpy.RepairGeometry_management(fc)
            errorsFound = res.maxSeverity > 0
            loopCount += 1
        if errorsFound:
            printMsg("unable to repair all errors in {0}".format(arcpy.Describe(fc).name), msgType=WARNING)
    except Exception as e:
        printMsg(str(e), msgType=WARNING)
        pass


#-----------------------------------------------------------------------------------------------------------------------
# Execute Eliminate_management in a loop until no more slivers can be eliminated, then delete remaining slivers.
#   fc: feature class from which to eliminate slivers
#   sliverSize: value (length or area) below which a feature is defined as a sliver
#   maxIterations (optional): maximum number of eliminate loops (some slivers may remain)
#   method (optional): selection method used to eliminate slivers (should match sliverSize value)
def eliminateSlivers(fc, sliverSize, maxIterations=5, method="AREA"):
    explodeFc = fc + "_explode"
    arcpy.MultipartToSinglepart_management(fc, explodeFc)
    replace(fc, explodeFc)
    whereClause = '"Shape_Area" < {0}'.format(str(sliverSize))

    sliverLyr = arcpy.MakeFeatureLayer_management(fc, "sliverLyr")
    arcpy.SelectLayerByAttribute_management(sliverLyr, "NEW_SELECTION", whereClause)
    sliverCount = getCount(sliverLyr)

    totalSlivers = sliverCount

    if totalSlivers:
        printMsg("eliminating {0} slivers...".format(str(totalSlivers)))
        eliminateFc = fc + "_eliminate"
        loopCount = 1
        before = getCount(fc)
        after = 0
        while sliverCount and loopCount <= maxIterations and after != before:
            printMsg("  pass " + str(loopCount))
            # merge slivers with neighboring polygons of greatest area or longest border (use "LENGTH" for longest border)
            before = getCount(fc)
            arcpy.Eliminate_management(sliverLyr, eliminateFc, selection=method)
            replace(fc, eliminateFc)
            after = getCount(fc)

            sliverLyr = arcpy.MakeFeatureLayer_management(fc, "sliverLyr")
            arcpy.SelectLayerByAttribute_management(sliverLyr, "NEW_SELECTION", whereClause)
            sliverCount = getCount(sliverLyr)

            loopCount += 1
        if sliverCount:
            printMsg("  deleting {0} remaining slivers...".format(str(sliverCount)))
            arcpy.DeleteFeatures_management(sliverLyr)

    arcpy.Delete_management(sliverLyr)


#-----------------------------------------------------------------------------------------------------------------------
# Move feature geometries by offsetting centroids.
def moveFeatures(fc, offsetX, offsetY):
    with arcpy.da.UpdateCursor(fc, ["SHAPE@XY"]) as uCursor:
        for row in uCursor:
            uCursor.updateRow([[row[0][0] + offsetX, row[0][1] + offsetY]])


#-----------------------------------------------------------------------------------------------------------------------
# Trim lines to designated length.
def trimLines(linesFc, toLength, bothEnds=True, inPlace=True, tolerance=0.01):
    desc = arcpy.Describe(linesFc)
    sr = desc.spatialReference
    linesFcName = desc.name
    # splitPtsFc will be used to trim lines
    splitPtsFc = arcpy.CreateFeatureclass_management(env.workspace, linesFcName + '_splitpts_' + str(datetime.datetime.now().microsecond), 'POINT', spatial_reference=sr)
    # deletePtsFc will be used to remove leftover segments by intersection with segments
    deletePtsFc = arcpy.CreateFeatureclass_management(env.workspace, linesFcName + '_delpts_' + str(datetime.datetime.now().microsecond), 'POINT', spatial_reference=sr)

    arcpy.CreateFeatureclass_management(env.workspace, linesFcName + "_trimmed", template=linesFc)
    trimmedLinesFc = os.path.join(env.workspace, linesFcName + "_trimmed")

    linesFcLyr = "linesFclyr"
    arcpy.MakeFeatureLayer_management(linesFc, linesFcLyr)
    oidField = arcpy.Describe(linesFc).OIDFieldName

    with arcpy.da.SearchCursor(linesFc, [oidField, "SHAPE@", "SHAPE@LENGTH"]) as sCursor:
        for row in sCursor:

            splitPts = []
            deletePts = []
            arcpy.DeleteFeatures_management(splitPtsFc)
            arcpy.DeleteFeatures_management(deletePtsFc)

            lineId = row[0]
            line = row[1]
            lineLength = row[2]
            trimLength = lineLength - toLength

            arcpy.SelectLayerByAttribute_management(linesFcLyr, "NEW_SELECTION", '"{0}" = {1}'.format(oidField, str(lineId)))

            # if trimLength <= 0 or trimLength < tolerance, skip line
            if trimLength <= 0 or trimLength < tolerance:
                arcpy.Append_management(linesFcLyr, trimmedLinesFc)
            # else trim
            else:
                if bothEnds:
                    # add start and end points to deletePtsFc
                    deletePts.extend([line.firstPoint, line.lastPoint])
                    # add split points at (trimLength / 2) distance from start and end of line
                    splitPt1 = line.positionAlongLine(trimLength / 2)
                    splitPt2 = line.positionAlongLine(lineLength - trimLength / 2)
                    splitPts.extend([splitPt1, splitPt2])
                else:
                    # add end point to deletePtsFc
                    deletePts.append(line.lastPoint)
                    # add split point at (trimLength) distance from start of line
                    splitPt = line.positionAlongLine(trimLength)
                    splitPts.append(splitPt)

                # do these separately to avoid having to open an edit session
                with arcpy.da.InsertCursor(splitPtsFc, ["SHAPE@"]) as iCursor:
                    for p in splitPts:
                        iCursor.insertRow([p])
                with arcpy.da.InsertCursor(deletePtsFc, ["SHAPE@"]) as iCursor:
                    for p in deletePts:
                        iCursor.insertRow([p])

                # snap points to line for precise split/delete
                arcpy.Near_analysis(splitPtsFc, linesFcLyr, location="LOCATION")
                with arcpy.da.UpdateCursor(splitPtsFc, ["SHAPE@X", "SHAPE@Y", "NEAR_X", "NEAR_Y"]) as uCursor:
                    for row in uCursor:
                        row[0] = row[2]
                        row[1] = row[3]
                        uCursor.updateRow(row)
                arcpy.Near_analysis(deletePtsFc, linesFcLyr, location="LOCATION")
                with arcpy.da.UpdateCursor(deletePtsFc, ["SHAPE@X", "SHAPE@Y", "NEAR_X", "NEAR_Y"]) as uCursor:
                    for row in uCursor:
                        row[0] = row[2]
                        row[1] = row[3]
                        uCursor.updateRow(row)

                tempFc = trimmedLinesFc
                # trim lines
                if arcpy.Exists(tempFc):
                    tempFc = arcpy.CreateUniqueName(os.path.basename(trimmedLinesFc), os.path.dirname(trimmedLinesFc))
                arcpy.SplitLineAtPoint_management(linesFcLyr, splitPtsFc, tempFc, 0.01)

                # safety check: don't delete segments if only one line feature remains (i.e., split didn't have any effect)
                if getCount(tempFc) > 1:
                    # delete leftover segments
                    tempFcLyr = "tempFcLyr"
                    arcpy.MakeFeatureLayer_management(tempFc, tempFcLyr)
                    arcpy.SelectLayerByLocation_management(tempFcLyr, "INTERSECT", deletePtsFc, selection_type="NEW_SELECTION")
                    arcpy.DeleteFeatures_management(tempFcLyr)
                    arcpy.Delete_management(tempFcLyr)

                if tempFc != trimmedLinesFc:
                    arcpy.Append_management(tempFc, trimmedLinesFc)
                    arcpy.Delete_management(tempFc)

    arcpy.Delete_management(splitPtsFc)
    arcpy.Delete_management(deletePtsFc)
    arcpy.Delete_management(linesFcLyr)

    if inPlace:
        replace(linesFc, trimmedLinesFc)
        return linesFc
    else:
        return trimmedLinesFc


#-----------------------------------------------------------------------------------------------------------------------
# Make profile graph.
def makeProfileGraph(profileLines, profileTargets, profileTable, profileGraphName, profileGraphPath):
    # try:
    arcpy.StackProfile_3d(profileLines, profileTargets, profileTable, profileGraphName)
    arcpy.SaveGraph_management(profileGraphName, profileGraphPath)
    # except:
    #     printMsg("Unable to create profile graph. 3D Analyst extension is required.", ERROR)


#-----------------------------------------------------------------------------------------------------------------------
# Compare strings in UTF-8 encoding to enable comparison of unicode and non-unicode strings.
def utf8StringCompare(s1, s2):
    return s1.encode('UTF-8') == s2.encode('UTF-8')


#-----------------------------------------------------------------------------------------------------------------------
# Return full path including rootDir.
def getFullPath(rootDir, fullOrRelativePath):
    fullPath = ""
    if arcpy.Exists(fullOrRelativePath):
        fullPath = fullOrRelativePath
    else:
        fullPath = os.path.join(rootDir, fullOrRelativePath)
    if not arcpy.Exists(fullPath):
        printMsg("path not found: {0}".format(fullOrRelativePath), msgType=ERROR)
    return fullPath


#-----------------------------------------------------------------------------------------------------------------------
# Copy and convert a feature class to a shapefile or feature class.
def copyAndConvert(fc, destPath, destName):
    # FileGDBs seem to have a 27 character limit with filenames (thanks, ESRI)
    destDesc = arcpy.Describe(destPath)
    if destDesc.workspaceType != "FileSystem":
        tempDestName = destName + "_" + str(datetime.datetime.now().microsecond)
        cut = 0
        while len(tempDestName) > 27:
            cut -= 1
            tempDestName = destName[:cut] + "_" + str(datetime.datetime.now().microsecond)
    else:
        tempDestName = destName + "_" + str(datetime.datetime.now().microsecond)
    # this two-step copy/conversion ensures that geometries are converted to standard ESRI shapes
    tempPath = os.path.join(destPath, tempDestName)
    arcpy.CopyFeatures_management(fc, tempPath)
    arcpy.FeatureClassToFeatureClass_conversion(tempPath, destPath, destName)
    arcpy.Delete_management(tempPath)


#-----------------------------------------------------------------------------------------------------------------------
# Return closest key value.
def findClosestKeyVal(keyValDict, matchKey):
    if matchKey in keyValDict:
        return matchKey, keyValDict[matchKey]
    else:
        keys = sorted(keyValDict.keys())
        closestKey = findClosestVal(keys, matchKey)
        return closestKey, keyValDict[closestKey]


#-----------------------------------------------------------------------------------------------------------------------
# Return closest value in list.
def findClosestVal(sortedList, val):
    pos = bisect_left(sortedList, val)
    if pos == 0:
        return sortedList[0]
    if pos == len(val):
        return sortedList[-1]
    previous = sortedList[pos - 1]
    next = sortedList[pos]
    if (next - val) < (val - previous):
       return next
    else:
       return previous


#-----------------------------------------------------------------------------------------------------------------------
# Segment line at designated interval.
def segmentLineAtInterval(inLine, outName, interval, lineClusTol, ptFields=[], distanceFieldUnits="ft"):
    """Segments inLine by interval and outputs segmented version. If segment is less
    than lineClusTol, it gets merged to the previous segment. Optional param ptFields
    also outputs the segmentation points and allows for specification of fields to be
    included."""
    desc = arcpy.Describe(inLine)
    sr = desc.spatialReference
    inLineName = desc.name
    ptsName = outName + "_pts"
    if arcpy.Exists(ptsName):
        arcpy.Delete_management(ptsName)
    # Create empty point fc
    segPts = arcpy.CreateFeatureclass_management(env.workspace, ptsName, 'POINT', spatial_reference=sr)
    # Get list of inLine field objects
    inLineFields = [f for f in arcpy.ListFields(inLine)]

    distField = "station"
    arcpy.AddField_management(segPts, distField, "DOUBLE")

    # As Field method types and AddField types have different names, rename them
    for f in ptFields:
        typ = None
        for field in inLineFields:
            if field.name == f:
                typ = field.type
                break
        addTyp = typ
        if typ == 'Integer':
            addTyp = 'LONG'
        elif typ == 'SmallInteger':
            addTyp = 'SHORT'
        elif typ == 'String':
            addTyp = 'TEXT'
        elif typ == 'Single':
            addTyp = 'FLOAT'
        elif typ == 'Double':
            addTyp = 'DOUBLE'
        if addTyp:
            arcpy.AddField_management(segPts, f, addTyp)
        else:
            printMsg("'{0}' field not found in line fields".format(f), msgType=WARNING)

    shapeField = "SHAPE@"
    shapeLengthField = "SHAPE@LENGTH"

    #printMsg("preparing line segments for {0}: feature count = {1}".format(inLineName, str(arcpy.GetCount_management(inLine).getOutput(0))))

    iFields = [shapeField, distField] + ptFields
    sFields = [shapeLengthField, shapeField] + ptFields

    with arcpy.da.InsertCursor(segPts, iFields) as iCursor:
        with arcpy.da.SearchCursor(inLine, sFields) as sCursor:
            for row in sCursor:
                length = row[0]
                numIntervals = int(max(1, math.floor(length / interval)))
                lastSegLength = (length - interval * numIntervals) if (interval * numIntervals <= length) else length
                pts = []
                totalDistance = 0    # NOTE: totalDistance = straight line distance (doesn't account for curves)

                # calculate start point first in case numIntervals == 0 (line length < interval length)
                startPt = row[1].positionAlongLine(0)
                if ptFields:
                    iCursor.insertRow(tuple([startPt, totalDistance]) + row[2:])
                else:
                    iCursor.insertRow(tuple([startPt, totalDistance]))
                pts.append(startPt)

                for x in range(1, numIntervals):                        # start at 1 to exclude start point
                    newPt = row[1].positionAlongLine(interval * x)
                    if len(pts):
                        totalDistance += newPt.distanceTo(pts[-1])
                    if ptFields:
                        iCursor.insertRow(tuple([newPt, totalDistance]) + row[2:])
                    else:
                        iCursor.insertRow(tuple([newPt, totalDistance]))
                    pts.append(newPt)

                if lastSegLength < lineClusTol:
                    lastPt = row[1].positionAlongLine(interval * numIntervals + lastSegLength)
                    totalDistance += lastPt.distanceTo(pts[-1])
                else:
                    lastPt = row[1].positionAlongLine(interval * numIntervals)
                    totalDistance += lastPt.distanceTo(pts[-1])
                if ptFields:
                    iCursor.insertRow(tuple([lastPt, totalDistance]) + row[2:])
                else:
                    iCursor.insertRow(tuple([lastPt, totalDistance]))

                pts.append(lastPt)

    splitLine = arcpy.SplitLineAtPoint_management(inLine, segPts, outName, 0.5)

    if ptFields:
        return splitLine, segPts
    else:
        arcpy.Delete_management(segPts)
        return splitLine


#-----------------------------------------------------------------------------------------------------------------------
# Return line features delineating min or max values in raster corresponding to referenceLineFc features.
def delineateRasterMinOrMax(workspace, referenceLineFc, raster, sampleInterval, searchDistance, intervalFactor=4, MIN_OR_MAX="MIN", output3d=True):
    from sfei_transects import buildTransects

    if MIN_OR_MAX.lower() not in ["min", "max"]:
        raise Exception("'{0}' is not a valid MIN_OR_MAX value".format(str(MIN_OR_MAX)))

    minOrMax = min if MIN_OR_MAX.lower() == "min" else max

    overwriteSetting = arcpy.env.overwriteOutput
    arcpy.env.overwriteOutput = True

    sr = arcpy.Describe(referenceLineFc).spatialReference

    lineIdField = "line_id"
    transIdField = "trans_id"
    outputLine = os.path.join(workspace, arcpy.Describe(referenceLineFc).name + "_stat_" + MIN_OR_MAX)

    # add line ID field
    safeAddField(referenceLineFc, lineIdField, "LONG")
    with arcpy.da.UpdateCursor(referenceLineFc, ('OID@', lineIdField)) as uCursor:
        for row in uCursor:
            row[1] = row[0]
            uCursor.updateRow(row)

    printMsg("segmenting lines...")
    cellSize = (raster.meanCellHeight + raster.meanCellWidth) / 2
    segmentsName = "ref_segments"
    refSegments, refSegmentPts = segmentLineAtInterval(referenceLineFc, segmentsName, sampleInterval, cellSize, ptFields=[lineIdField])

    # add transect ID field
    safeAddField(refSegmentPts, transIdField, "LONG")
    with arcpy.da.UpdateCursor(refSegmentPts, ["OID@", transIdField]) as uCursor:
        for row in uCursor:
            row[1] = row[0]
            uCursor.updateRow(row)

    transectsName = "ref_transects"
    transects = buildTransects(referenceLineFc, lineIdField, transIdField=transIdField, outName=transectsName, transPts=refSegmentPts,
                               transLength=searchDistance, transSegLength=sampleInterval*intervalFactor)
    rasterClip = os.path.join(arcpy.env.scratchGDB, "clip_temp")
    extent = arcpy.Describe(transects).extent
    envelope = "{0} {1} {2} {3}".format(str(extent.XMin), str(extent.YMin), str(extent.XMax), str(extent.YMax))
    arcpy.Clip_management(raster, envelope, rasterClip)

    outputLine2d = outputLine + "_2d"
    if arcpy.Exists(outputLine2d):
        arcpy.Delete_management(outputLine2d)
    z_enabled = "ENABLED" if output3d else "DISABLED"
    arcpy.CreateFeatureclass_management(os.path.dirname(outputLine2d), os.path.basename(outputLine2d), "POLYLINE", has_z=z_enabled, spatial_reference=sr)
    safeAddField(outputLine2d, lineIdField, "LONG")

    transLyr = "trans_lyr"
    segmentsName = "trans_segments"
    arcpy.MakeFeatureLayer_management(transects, transLyr)

    printMsg("segmenting lines...")
    transSegments, transSegmentPts = segmentLineAtInterval(transLyr, segmentsName, cellSize, cellSize, ptFields=[transIdField, lineIdField])
    ptsLyr = arcpy.Describe(transSegmentPts).name + "_lyr"
    arcpy.MakeFeatureLayer_management(transSegmentPts, ptsLyr)

    printMsg("extracting raster values...")
    rasterValueField = "RASTERVALU" # "raster_value"
    # extract raster values to points
    #ExtractMultiValuesToPoints(ptsLyr, [[rasterClip, rasterValueField]], bilinear_interpolate_values="BILINEAR")
    ptValuesFc = arcpy.Describe(transSegmentPts).name + "_values"
    ExtractValuesToPoints(ptsLyr, rasterClip, ptValuesFc, interpolate_values="INTERPOLATE", add_attributes="ALL")
    arcpy.Delete_management(ptsLyr)
    arcpy.MakeFeatureLayer_management(ptValuesFc, ptsLyr)

    # set NoData values to None
    noDataValue = -9999
    arcpy.SelectLayerByAttribute_management(ptsLyr, "NEW_SELECTION", '"{0}" = {1}'.format(rasterValueField, str(noDataValue)))
    with arcpy.da.UpdateCursor(ptsLyr, [rasterValueField]) as uCursor:
        for row in uCursor:
            row[0] = None
            uCursor.updateRow(row)

    lineIds = sorted(set([row[0] for row in arcpy.da.SearchCursor(transLyr, [lineIdField])]))
    lineCount = len(lineIds)
    count = 1
    for lineId in lineIds:
        printMsg("processing line {0} of {1}...".format(str(count), str(lineCount)))
        arcpy.SelectLayerByAttribute_management(ptsLyr, "NEW_SELECTION", '"{0}" = {1}'.format(lineIdField, str(lineId)))

        transIds = sorted(set([row[0] for row in arcpy.da.SearchCursor(ptsLyr, [transIdField])]))

        pointArray = arcpy.Array()
        for trId in transIds:
            arcpy.SelectLayerByAttribute_management(ptsLyr, "NEW_SELECTION", '"{0}" = {1}'.format(transIdField, str(trId)))
            value = minOrMax([row[0] for row in arcpy.da.SearchCursor(ptsLyr, [rasterValueField]) if row[0] is not None])
            point = [pt[0] for pt in [row for row in arcpy.da.SearchCursor(ptsLyr, ["SHAPE@", rasterValueField])] if pt[1] == value][0]
            pointArray.add(arcpy.Point(point.centroid.X, point.centroid.Y))
            arcpy.DeleteFeatures_management(ptsLyr)

        line = arcpy.Polyline(pointArray)
        with arcpy.da.InsertCursor(outputLine2d, ["SHAPE@", lineIdField]) as iCursor:
            iCursor.insertRow([line, lineId])

        count += 1

    arcpy.Delete_management(transSegmentPts)
    arcpy.Delete_management(transSegments)
    arcpy.Delete_management(ptsLyr)
    arcpy.Delete_management(transLyr)

    if output3d:
        arcpy.InterpolateShape_3d(rasterClip, outputLine2d, outputLine)
        arcpy.Delete_management(outputLine2d)
    else:
        outputLine = outputLine2d

        outputLineLyr = os.path.basename(outputLine) + "_lyr"
        arcpy.MakeFeatureLayer_management(outputLine, outputLineLyr)

        lineFcName = arcpy.Describe(referenceLineFc).name + "_stat_temp"
        arcpy.FeatureClassToFeatureClass_conversion(referenceLineFc, workspace, lineFcName)
        lineLyr = lineFcName + "_lyr"
        lineFc = os.path.join(workspace, lineFcName)
        arcpy.MakeFeatureLayer_management(lineFc, lineLyr)

        # replace geometries in original fc
        lineIds = sorted(set([row[0] for row in arcpy.da.SearchCursor(outputLine, [lineIdField])]))
        for lineId in lineIds:
            whereClause = '"{0}" = {1}'.format(lineIdField, str(lineId))
            arcpy.SelectLayerByAttribute_management(lineLyr, "NEW_SELECTION", whereClause)
            arcpy.SelectLayerByAttribute_management(outputLineLyr, "NEW_SELECTION", whereClause)
            lineGeom = [row[0] for row in arcpy.da.SearchCursor(outputLineLyr, ["SHAPE@"])][0]
            with arcpy.da.UpdateCursor(lineLyr, ["SHAPE@"]) as uCursor:
                for row in uCursor:
                    row[0] = lineGeom
                    uCursor.updateRow(row)

        replace(outputLine, lineFc)

        arcpy.Delete_management(outputLineLyr)
        arcpy.Delete_management(lineLyr)

    arcpy.Delete_management(rasterClip)
    arcpy.Delete_management(refSegments)
    arcpy.Delete_management(refSegmentPts)
    arcpy.Delete_management(transects)

    arcpy.env.overwriteOutput = overwriteSetting

    return outputLine


#---------------------------------------------------------------------------------------------------------
# temporary(?) wrappers for os.startfile and webbrowser.open to work in arcpy
# see https://arcpy.wordpress.com/2013/10/25/using-os-startfile-and-webbrowser-open-in-arcgis-for-desktop/

import functools
import os
import threading
import webbrowser

# A decorator that will run its wrapped function in a new thread
def run_in_other_thread(function):
    # functool.wraps will copy over the docstring and some other metadata
    # from the original function
    @functools.wraps(function)
    def fn_(*args, **kwargs):
        thread = threading.Thread(target=function, args=args, kwargs=kwargs)
        thread.start()
        thread.join()
    return fn_

# Our new wrapped versions of os.startfile and webbrowser.open
startfile = run_in_other_thread(os.startfile)
openbrowser = run_in_other_thread(webbrowser.open)
#---------------------------------------------------------------------------------------------------------