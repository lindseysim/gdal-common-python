import datetime
import calendar

__DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def getDayOfYear(dt):
    return dt.timetuple().tm_yday

def addYear(dt, years):
    return dt.replace(year=dt.year+years)

def addDays(dt, days):
    return dt + datetime.timedelta(days=days)

def addHours(dt, hours):
    return dt + datetime.timedelta(hours=hours)

def addMinutes(dt, minutes):
    return addSeconds(dt, 60*minutes)

def addSeconds(dt, seconds):
    return dt + datetime.timedelta(seconds=seconds)

def checkLeapYear(year):
    return year % 4 == 0

def daysInMonth(month, year=None):
    if month <= 0 or month > 12:
        return 0
    days = __DAYS_IN_MONTH[month]
    if month == 2 and year is not None and checkLeapYear(year):
        days += 1
    return days

def getMonthName(month):
    if month <= 0 or month > 12:
        return ""
    return calendar.month_name[month]

def getMonthAbbreviation(month):
    if month <= 0 or month > 12:
        return ""
    return calendar.month_abbr[month]
