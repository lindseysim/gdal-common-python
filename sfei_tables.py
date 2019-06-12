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
import csv
from collections import defaultdict


#-----------------------------------------------------------------------------------------------------------------------
# Import table to geodatabase. Fills spaces in table name if necessary.
#   table: full path to table
#   gdb: full path to destination geodatabase
#   name (optional): destination table name--if unspecified, source table name will be used
def importTable(table, gdb, name=''):
    from sfei_utils import fillSpaces
    if name:
        tableName = name
    else:
        tableName = fillSpaces(os.path.splitext(os.path.basename(table))[0]) # spaces in table names are not allowed
    arcpy.TableToTable_conversion(table, gdb, tableName)
    return os.path.join(gdb, tableName)


#-----------------------------------------------------------------------------------------------------------------------
# Create geodatabase table.
# fieldTuples format: [ (field1_name, field1_type), (field2_name, field2_type), .. (fieldn_name, fieldn_type) ]
# Example:
#   fieldTuples = [ ("cityName", "TEXT"), ("area", "FLOAT"), ("population", "INTEGER") ]
def createTable(gdb, tableName, fieldTuples):
    res = arcpy.CreateTable_management(gdb, tableName)
    for f in fieldTuples:
        arcpy.AddField_management(os.path.join(gdb, tableName), f[0], f[1])
    return res.getOutput(0)


#-----------------------------------------------------------------------------------------------------------------------
# Create geodatabase table from dict.
# fieldTuples format: [ (field1_name, field1_type), (field2_name, field2_type), .. (fieldn_name, fieldn_type) ]
# rowDict is keyed by field1 value and contains list of field2..fieldn values
# Example:
#   fieldTuples = [ ("cityName", "TEXT"), ("area", "FLOAT"), ("population", "INTEGER") ]
#   rowDict = { "San Francisco" : [46.9, 805235], "San Rafael" : [22.4, 57713] }
def dictToTable(gdb, tableName, fieldTuples, rowDict):
    table = createTable(gdb, tableName, fieldTuples)
    with arcpy.da.InsertCursor(table, [f[0] for f in fieldTuples]) as iCursor:
        for key in rowDict.keys():
            values = [key] + rowDict[key]
            iCursor.insertRow(values)


#-----------------------------------------------------------------------------------------------------------------------
# Load table into dict of dicts. Row values are accessed by field name.
def tableToDictOfDicts(table):
    tableDict = defaultdict(dict)
    fields = [f.name for f in arcpy.ListFields(table)]
    with arcpy.da.SearchCursor(table, fields) as sCursor:
        for row in sCursor:
            tableDict[row[0]] = dict(zip(fields, row))
    return tableDict


#-----------------------------------------------------------------------------------------------------------------------
# Load table into dict of lists. Row values are accessed by index.
def tableToDictOfLists(table):
    tableDict = defaultdict(dict)
    fields = [f.name for f in arcpy.ListFields(table)]
    with arcpy.da.SearchCursor(table, fields) as sCursor:
        for row in sCursor:
            tableDict[row[0]] = [row[i] for i in range(0, len(row))]
    return tableDict


#-----------------------------------------------------------------------------------------------------------------------
# Export table or feature class to csv.
def tableToCSV(inputTable, csvPath):
    with open(csvPath, 'ab+') as csvfile:
        writer = csv.writer(csvfile, 'excel')
        csvHdr = [tbl_fld.aliasName for tbl_fld in arcpy.ListFields(inputTable, "*")]
        writer.writerow(csvHdr)
        tblFldNms = [tbl_fld.name for tbl_fld in arcpy.ListFields(inputTable, "*")]
        sCursor = arcpy.SearchCursor(inputTable)
        for scRow in sCursor:
            rowValues = []
            for tblFldNm in tblFldNms:
                rowValues.append(scRow.getValue(tblFldNm))
            writer.writerow(rowValues)