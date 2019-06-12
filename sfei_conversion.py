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

import math

CM_TO_IN = 0.393701
IN_TO_CM = 2.54
FT_TO_M = 0.3048
M_TO_FT = 3.28084
SQ_FT_TO_SQ_M = 0.092903
SQ_M_TO_SQ_FT = 10.7639
SQ_MI_TO_SQ_M = 2.58999e6
SQ_M_TO_SQ_MI = 3.86102e-7
AC_TO_SQ_M = 4046.86
SQ_M_TO_AC = 0.000247105
MI_TO_KM = 1.60934
KM_TO_MI = 0.621371
SQ_M_TO_SQ_KM = 0.000001
SQ_KM_TO_SQ_M = 1000000
SQ_KM_TO_SQ_MI = 0.386102
SQ_MI_TO_SQ_KM = 2.58999
SQ_MI_TO_AC = 640
AC_TO_SQ_MI = 0.0015625
HA_TO_AC = 2.47105
AC_TO_HA = 0.404686
M_TO_KM = 0.001
KM_TO_M = 1000
G_TO_KG = 0.001
KG_TO_G = 1000
MM_TO_M = 0.001
M_TO_MM = 1000

def cmToIn(cm):
    return cm * CM_TO_IN

def inToCm(inches):
    return inches * IN_TO_CM

def mmToCm(mm):
    return mm * 0.1

def cmToMm(cm):
    return cm * 10

def mmToM(mm):
    return mm * MM_TO_M

def mToMm(m):
    return m * M_TO_MM

def ftToM(ft):
    return ft * FT_TO_M

def mToFt(m):
    return m * M_TO_FT

def sqFtToSqM(sqft):
    return sqft * SQ_FT_TO_SQ_M

def sqMToSqFt(sqM):
    return sqM * SQ_M_TO_SQ_FT

def sqMToSqMi(sqM):
    return sqM * SQ_M_TO_SQ_MI

def sqMToAc(sqM):
    return sqM * SQ_M_TO_AC

def sqMiToSqM(sqMi):
    return sqMi * SQ_MI_TO_SQ_M

def sqMToSqKm(sqM):
    return sqM * SQ_M_TO_SQ_KM

def sqKmToSqM(sqKm):
    return sqKm * SQ_KM_TO_SQ_M

def miToKm(mi):
    return mi * MI_TO_KM

def kmToMi(km):
    return km * KM_TO_MI

def sqMiToSqKm(sqMi):
    return sqMi * SQ_MI_TO_SQ_KM

def sqKmToSqMi(sqKm):
    return sqKm * SQ_KM_TO_SQ_MI

def sqMiToAc(sqMi):
    return sqMi * SQ_MI_TO_AC

def acToSqMi(ac):
    return ac * AC_TO_SQ_MI

def haToAc(ha):
    return ha * HA_TO_AC

def acToHa(ac):
    return ac * AC_TO_HA

def mToKm(m):
    return m * M_TO_KM

def kmToM(km):
    return km * KM_TO_M

def gToKg(g):
    return g * G_TO_KG

def kgToG(kg):
    return kg * KG_TO_G

def degToPctSlope(degSlope):
    return math.tan(math.radians(degSlope))

def pctToDegSlope(pctSlope):
    return math.degrees(math.atan(pctSlope/float(100)))
