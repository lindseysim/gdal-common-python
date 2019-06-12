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

# array of objects to be deleted
_TRASH = []

def addTrash(items):
    global _TRASH
    if isinstance(items, list):
        _TRASH.extend(items)
    else:
        _TRASH.append(items)

def emptyTrash():
    global _TRASH
    for obj in _TRASH:
        try:
            arcpy.Delete_management(obj)
        except:
            pass
    _TRASH = []
