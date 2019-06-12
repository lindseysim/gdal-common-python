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
import time
import datetime


#-----------------------------------------------------------------------------------------------------------------------
# Format time elapsed.
def formatTime(t):
    return str(datetime.timedelta(seconds=round(time.clock() - t)))


#-----------------------------------------------------------------------------------------------------------------------
# Create readable timestamp.
def timeStamp(a):
    tdict = {
    'mon' : str(a.tm_mon),
    'day' : str(a.tm_mday),
    'year' : str(a.tm_year),
    'hour' : str(a.tm_hour),
    'min' : str(a.tm_min),
    'sec' : str(a.tm_sec)}
    for label, digit in tdict.items():
        if int(digit) < 10:
            tdict[label] = "0" + digit
    return tdict['mon'] + '/' + tdict['day'] + '/' + tdict['year'] + ', ' + tdict['hour'] + ':' + tdict['min'] + ':' + tdict['sec']


#-----------------------------------------------------------------------------------------------------------------------
# Format timestamp without spaces (can be used as file name).
def formatTimeStamp():
    return datetime.datetime.now().strftime('%Y.%m.%d_%H.%M.%S')


#-----------------------------------------------------------------------------------------------------------------------
# Create geodatabase named with timestamp and optional prefix and suffix.
def createTimeStampedGdb(workspace, prefix="", suffix=""):
    gdb = os.path.join(workspace, "{0}{1}{2}{3}".format(prefix, formatTimeStamp(), suffix, '.gdb'))
    arcpy.CreateFileGDB_management(os.path.dirname(gdb), os.path.basename(gdb))
    return gdb


#-----------------------------------------------------------------------------------------------------------------------
# Format verbose time.
def formatTimeVerbose(dt=None):
    format = "%a %b %d %Y %H:%M:%S "
    if not dt:
        dt = datetime.datetime.now()
    return dt.strftime(format)
