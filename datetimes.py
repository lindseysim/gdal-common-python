import datetime
import calendar


__DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def dayOfYear(dt):
    '''
    Get day of year from 1-365 (or 366 if leap year).
    :param dt: (datetime) The datetime of interest.
    :return: (int)
    '''
    return dt.timetuple().tm_yday


def addYear(dt, years):
    '''
    :param dt: (datetime) The datetime to 'modify' (as datetimes are immutable, returns modified copy).
    :param years: (int) The years to add (or subtract, if negative).
    :return: (datetime)
    '''
    return dt.replace(year=dt.year+years)


def addDays(dt, days):
    '''
    :param dt: (datetime) The datetime to 'modify' (as datetimes are immutable, returns modified copy).
    :param years: (int) The days to add (or subtract, if negative).
    :return: (datetime)
    '''
    return dt + datetime.timedelta(days=days)


def addHours(dt, hours):
    '''
    :param dt: (datetime) The datetime to 'modify' (as datetimes are immutable, returns modified copy).
    :param years: (int) The hours to add (or subtract, if negative).
    :return: (datetime)
    '''
    return dt + datetime.timedelta(hours=hours)


def addMinutes(dt, minutes):
    '''
    :param dt: (datetime) The datetime to 'modify' (as datetimes are immutable, returns modified copy).
    :param years: (minutes) The minutes to add (or subtract, if negative).
    :return: (datetime)
    '''
    return addSeconds(dt, 60*minutes)


def addSeconds(dt, seconds):
    '''
    :param dt: (datetime) The datetime to 'modify' (as datetimes are immutable, returns modified copy).
    :param years: (seconds) The seconds to add (or subtract, if negative).
    :return: (datetime)
    '''
    return dt + datetime.timedelta(seconds=seconds)


def isLeapYear(year):
    '''
    Check if year is a leap year.
    :param year: (int) The year.
    :return: (boolean) True if it is a leap year.
    '''
    return year % 4 == 0


def daysInMonth(month, year=None):
    '''
    Get number of days in the given month.
    :param month: (int) Month number from 1-12.
    :param [year]: (int) Year number, to account for leap years, if applicable.
    :return: (int)
    '''
    if month <= 0 or month > 12:
        return 0
    days = __DAYS_IN_MONTH[month]
    if month == 2 and year is not None and isLeapYear(year):
        days += 1
    return days


def getMonthName(month):
    '''
    Get name of the month.
    :param month: (int) Month number from 1-12.
    :return: (str)
    '''
    if month <= 0 or month > 12:
        return ""
    return calendar.month_name[month]


def getMonthAbbreviation(month):
    '''
    Get abbreviation of the month name.
    :param month: (int) Month number from 1-12.
    :return: (str)
    '''
    if month <= 0 or month > 12:
        return ""
    return calendar.month_abbr[month]
