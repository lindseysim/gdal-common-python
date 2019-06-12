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


import csv


#-----------------------------------------------------------------------------------------------------------------------
# Write dict to csv with row format [key, value]. The file is overwritten if it already exists.
#   csvPath: full path to csv file
#   theDict: dict object
def dictToCsv(csvPath, theDict):
    with open(csvPath, 'wb') as csvfile:
        writer = csv.writer(csvfile, 'excel')
        for key in sorted(theDict.keys()):
            writer.writerow([str(key), str(theDict[key])])


#-----------------------------------------------------------------------------------------------------------------------
# Write tool summary information to csv. The file is appended to if it already exists.
#   csvPath: full path to csv file
#   toolName: name to identify tool in summary
#   parameterDict (optional): tool parameter dict
#   messages (optional): tool messages
#   clock (optional): tool processing time clock
def writeSummaryCsv(csvPath, toolName, parameterDict={}, messages=[], clock=None):
    from sfei_utils import formatTime
    with open(csvPath, 'ab+') as csvfile:
        writer = csv.writer(csvfile, 'excel')
        writer.writerow([toolName])
        writer.writerow([])
        writer.writerow(["Tool parameters:"])
        for key in sorted(parameterDict.keys()):
            writer.writerow([str(key), parameterDict[key].valueAsText])
        writer.writerow([])
        writer.writerow(["Messages:"])
        for message in messages:
            writer.writerow([message])
        writer.writerow([])
        if clock:
            writer.writerow(["Total processing time: " + formatTime(clock)])
            writer.writerow([])
        writer.writerow([])
