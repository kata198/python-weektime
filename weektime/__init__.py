#!/usr/bin/env python
'''
    Copyright (c) 2016 Tim Savannah
'''

import datetime
import os
import re
import time


__version__ = '1.0.0'
__version_tuple__ = (1, 0, 0)

__all__ = ('getWeekDayAbbreviations', 'getWeekDayNames', 'dayStrToNumber', 'WeekRange', 'WeekRanges', 'WeekRangeValueError')

# Regular expression for a single week range. Optional day. Can be specified like Mon 12:00 - Tue 13:00 or 12:00 - 13:00. The field names unroll directly to WeekRange constructor
WEEK_RANGE_RE = re.compile('^[ ]*(?P<startDay>[a-zA-Z]{3}){0,1}[ ]*(?P<startHour>[\d]{1,2}):(?P<startMinute>[\d]{1,2})[ ]*[-][ ]*(?P<endDay>[a-zA-Z]{3}){0,1}[ ]*(?P<endHour>[\d]{1,2}):(?P<endMinute>[\d]{1,2})[ ]*$')

# Check for the types that could hold a string. Don't count "bytes"
try:
    unicode
    _str_types = (unicode, str)
except NameError:
    _str_types = (str, )

def getWeekDayNames(abbreviated=False):
    '''
        getWeekDayNames - Gets a list of week day names in current locale, starting with Monday.

        @param abbreviated <bool> - Default False, if True the return will be the locale's abbreviations. Otherwise, the full names.

        @return - A list of week day names. This is a general purpose function, for actual use within WeekRange use "getWeekDayAbbreviations" which computes once

            example return: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    '''
    # I know this is kinda hackish, but I can't find a standard way to do this. 
    #   You'd think datetime.datetime.strptime('1', '%w').strftime('%a') would do it, but always returns "Mon" regardless of number defined.
    now = datetime.datetime.now()
    thisDayNum = int(now.strftime('%w'))

    if abbreviated is True:
        strfDirective = '%a'
    else:
        strfDirective = '%A'

    if thisDayNum == 0:
        sunday = now
    else:
        sunday = now - datetime.timedelta(days=thisDayNum)

    return [sunday.strftime(strfDirective)] + [(sunday + datetime.timedelta(days=i)).strftime(strfDirective) for i in range(1, 7, 1)]

__weekDayAbbreviations = None
def getWeekDayAbbreviations(lower=False):
    '''
        getWeekDayAbbreviations - Gets a list of week day abbreviations in current locale, starting with Monday.

        @param lower <bool> - Default False, if True the week day names will be lowercased.

        @return - A list of week day abbreviations. This is calculated once, but the return value is a copy so you can modify it safely.

            example return: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    '''
    global __weekDayAbbreviations
    if __weekDayAbbreviations is None:
        __weekDayAbbreviations = getWeekDayNames(abbreviated=True)

    if lower is True:
        return [x.lower() for x in __weekDayAbbreviations]

    return [x for x in __weekDayAbbreviations]

def dayStrToNumber(dayStr):
    '''
        Converts a day string to a number representing the day of the week. Sun = 0, Sat = 6

        @param dayStr <str> - String of day

        @return <int> - Number of day of week.
    '''
    if dayStr.isdigit():
        dayNum = int(dayStr)
        if dayNum >= 7: # Don't need to check 0 because .isdigit() is False for negative numbers
            raise WeekRangeValueError('Day "%s" provided to WeekRange is invalid. Should be a number (Sunday=0 to Saturday=6) or a three-letter abbreviation matching current locale (like "Mon" for Monday in English)' %(dayStr,))
        return dayNum

    dayStr = dayStr.lower()
    if len(dayStr) > 3:
        # Technically not allowed, but we can work with it... Maybe we should allow it, and modify the regular expression to support it.
        dayStr = dayStr[:3]
    weekDayAbbreviations = getWeekDayAbbreviations(lower=True)

    try:
        return weekDayAbbreviations.index(dayStr)
    except:
        raise WeekRangeValueError('Day "%s" provided to WeekRange is invalid. Should be a number (Sunday=0 to Saturday=6) or a three-letter abbreviation matching current locale (like "Mon" for Monday in English)' %(dayStr,))


class WeekRange(object):
    '''
        WeekRange - Represents a span of time relative to a week. Provides means to check intersections and create from string.

        Use with #WeekRanges for multiple ranges, like 9AM to 6PM Mon-Fri.

        Supports both inner and outer ranges. So you can have "Mon 00:00 - Tue 12:01" to go from Monday to Tuesday at noon,  and also "Tue 00:00 - Mon 12:01" to go from Tuesday to the following Monday at noon.

        The range is left-inclusive and right-exclusive. That is you're within the range on the first minute of the "start" (left) side, and outside the range on the first minute of the "end" (right) side.

        Optimized to perform as many calculations ahead of time (optimizations based on the range itself) and to pick an optimized comparison function. This saves time, especially when your application
            may need to compare dates and times aganist week-level ranges often.
        Once created, the WeekRange object is immutable. If you need to change a value, create a new object.

        Use the "intersects" method to test if a datetime object falls within this week range.

        Use the "createFromStr" method to create a WeekRange from a time string, otherwise use the constructor directly.
        
        Examples:

            Check if now is between 9AM and 6PM:

                myRange = WeekRange.createFromStr('09:00 - 18:00')
                if myRange.intersects(datetime.datetime.now()):
                    ...

            Check if now is between 10AM on Tuesday to 1PM on Saturday:

                myRange = WeekRange.createFromStr('Tue 10:00 - Sat 13:00')
                if myRange.intersects(datetime.datetime.now()):
                    ...
    '''

    __slots__ = ('startDay', 'startHour', 'startMinute', 'endDay', 'endHour', 'endMinute', 'intersects', 'isSetup')

    def __init__(self, startDay, startHour, startMinute, endDay, endHour, endMinute):
        self.isSetup = False

        if isinstance(startDay, _str_types):
            self.startDay = dayStrToNumber(startDay)
        elif startDay is None:
            self.startDay = None
        else:
            self.startDay = int(startDay)
        self.startHour = int(startHour)
        self.startMinute = int(startMinute)

        if isinstance(endDay, _str_types):
            self.endDay = dayStrToNumber(endDay)
        elif endDay is None:
            self.endDay = None
        else:
            self.endDay = int(endDay)
        self.endHour = int(endHour)
        self.endMinute = int(endMinute)
        
#        print ( str(locals()) + '\n')

        if self.endDay is None and self.startDay is not None:
            # Allow ranges like  Mon 12:00 - 18:00 , but not Mon 18:00 - 12:00
            if self.endHour > self.startHour or (self.endHour == self.startHour and self.endMinute > self.startMinute):
                self.endDay = self.startDay
            else:
                raise WeekRangeValueError('Start and end day must both be empty, both defined, or start day may be defined if the end time is AFTER the start time (i.e. Mon 12:00 - 18:00 is okay, but Mon 18:00 - 12:00 is not)')


        if self.startDay is None:
            if self.endDay is not None:
                raise WeekRangeValueError('Start and end day must both be empty or both be defined.')
            if self.startHour > self.endHour:
                self.intersects = self._intersectsTimeOnlyOuter
            elif self.startHour == self.endHour:
                if self.startMinute > self.endMinute:
                    self.intersects = self._intersectsTimeOnlyOuterMinOnly
                elif self.startMinute == self.endMinute:
                    raise WeekRangeValueError('Start and end time cannot be the same.')
                else:
                    self.intersects = self._intersectsTimeOnlyInnerMinOnly
            else:
                self.intersects = self._intersectsTimeOnlyInner
        else:
            if self.startDay > self.endDay:
                self.intersects = self._intersectsOuter
            elif self.startDay == self.endDay:
                if self.startHour > self.endHour:
                    self.intersects = self._intersectsOuterSameDay
                elif self.startHour == self.endHour:
                    if self.startMinute > self.endMinute:
                        self.intersects = self._intersectsOuterSameDaySameHour
                    elif self.startMinute == self.endMinute:
                        raise ValueError('Start and end time cannot be the same.')
                    else:
                        self.intersects = self._intersectsInnerSameDaySameHour
                else:
                    self.intersects = self._intersectsInnerSameDay
            else:
                self.intersects = self._intersectsInner

        self.isSetup = True

#    def intersects(self, datetimeObj):
#        raise ValueError('WeekRange.intersects cannot be used statically. Create an object to set the correct "intersects" method.')


    @classmethod
    def createFromStr(cls, rangeStr):
        '''
            createFromStr - Create a WeekRange (or whatever class extends it) based off the provided range str.

            @param rangeStr <str> - Should be a string that represents a range str.   "DAY HH:MM - DAY HH:MM" -- where Day is optional. 
                You can specify either no day on either start or end side, or if the end time is after the start time, you can omit the end day and its value will be assigned the start day.
                If you specify no day, every day will match the time range.

                Example: Mon 12:00 - 15:00    or   Mon 12:00 - Tue 15:00   or   12:00 - 15:00
        '''
        matchObj = WEEK_RANGE_RE.match(rangeStr)
        if not matchObj:
            raise ValueError('Provided time string to WeekRange.createFromStr does not match expected format. Got "%s", was expecting "(optional 3-letter abbrev for day) HH:MM - (opt day) HH:MM". E.x. Mon 12:00 - Tue 12:35' %(rangeStr,))
        return cls(**matchObj.groupdict())


    def __setattr__(self, attrName, attrValue):
        if attrName == 'isSetup' and getattr(self, 'isSetup', False) is False:
            return object.__setattr__(self, attrName, attrValue)
        if self.isSetup is True:
            raise AttributeError('WeekRange is immutable. Create a new object instead of modifying this one.')

        return object.__setattr__(self, attrName, attrValue)

    def _intersectsTimeOnlyOuterMinOnly(self, datetimeObj):
        # same hour, going outer. So False if inner is match
        minute = datetimeObj.minute
        if minute >= self.endMinute and minute < self.startMinute:
            return False
        return True

    def _intersectsTimeOnlyInnerMinOnly(self, datetimeObj):
        # same hour, going inner.
        if datetimeObj.hour != self.startHour:
            return False

        minute = datetimeObj.minute
        if minute < self.startMinute or minute >= self.endMinute:
            return False

        return True

    def _intersectsTimeOnlyOuter(self, datetimeObj):
        # startHour and endHour are not equal. And going outer. False if inner is match

        # 13 55  12 20   12 56
        (hour, minute) = (datetimeObj.hour, datetimeObj.minute)
        if hour < self.startHour and hour > self.endHour:
            return False
        
        if hour == self.startHour:
            if minute < self.startMinute:
                return False
            return True

        if hour == self.endHour:
            if minute >= self.endMinute:
                return False
            return True

        return True

    def _intersectsTimeOnlyInner(self, datetimeObj):
        # startHour and endHour are not equal
        (hour, minute) = (datetimeObj.hour, datetimeObj.minute)
        # 12 20  13 55   12 56
        
        if hour == self.startHour:
            if minute >= self.startMinute:
                return True
            return False

        if hour == self.endHour:
            if minute < self.endMinute:
                return True
            return False

        if hour < self.startHour or hour > self.endHour:
            return False

        return True

    def _intersectsInner(self, datetimeObj):
        (day, hour, minute) = (int(datetimeObj.strftime('%w')), datetimeObj.hour, datetimeObj.minute)
        import pdb; pdb.set_trace()

        if day < self.startDay or day > self.endDay:
            return False

        if day == self.startDay:
            if hour > self.startHour:
                return True
            if hour == self.startHour and minute >= self.startMinute:
                return True
            return False

        if day == self.endDay:
            if hour < self.endHour:
                return True
            if hour == self.endHour and minute < self.endMinute:
                return True
            return False

        return True

    def _intersectsInnerSameDay(self, datetimeObj):
        # Day is same, hour different, inner range.
        (day, hour, minute) = (int(datetimeObj.strftime('%w')), datetimeObj.hour, datetimeObj.minute)

        if day != self.startDay:
            return False

        if hour < self.startHour or hour > self.endHour:
            return False

        if hour == self.startHour and minute >= self.startMinute:
            return True

        if hour == self.endHour and minute < self.endMinute:
            return True

        return False

    def _intersectsInnerSameDaySameHour(self, datetimeObj):
        # Day is same, hour same, inner range.
        (day, hour, minute) = (int(datetimeObj.strftime('%w')), datetimeObj.hour, datetimeObj.minute)

        if day != self.startDay or hour != self.startHour:
            return False

        if minute >= self.startMinute and minute < self.endMinute:
            return True

        return False

    def _intersectsOuter(self, datetimeObj):
        (day, hour, minute) = (int(datetimeObj.strftime('%w')), datetimeObj.hour, datetimeObj.minute)
        # 4 10 00 -> 1 20 00   

        if day > self.endDay and day < self.startDay:
            return False

        if day == self.startDay:
            if hour < self.startHour:
                return False
            if hour == self.startHour and minute < self.startMinute:
                return False
            return True

        if day == self.endDay:
            if hour > self.endHour:
                return False
            if hour == self.endHour and minute >= self.endMinute:
                return False
            return True
        
        return True

    def _intersectsOuterSameDay(self, datetimeObj):
        #Day is same, hour different, outer range

        # 4 10 00 -> 4 08 15
        (day, hour, minute) = (int(datetimeObj.strftime('%w')), datetimeObj.hour, datetimeObj.minute)

        if day != self.startDay:
            return True

        if hour > self.startHour or hour < self.endHour:
            return True

        if hour == self.startHour:
            if minute >= self.startMinute:
                return True
            return False

        if hour == self.endHour:
            if minute < self.endMinute:
                return True
            return False
        
        return False

    def _intersectsOuterSameDaySameHour(self, datetimeObj):
        # 4 10 21 4 10 10
        (day, hour, minute) = (int(datetimeObj.strftime('%w')), datetimeObj.hour, datetimeObj.minute)

        if day != self.startDay or hour != self.startHour:
            return True

        if minute < self.startMinute and minute >= self.endMinute:
            return False

        return True

    def __repr__(self):
        return self.__class__.__name__ + '(%s, %d, %d, %s, %d, %d)' %(repr(self.startDay), self.startHour, self.startMinute, repr(self.endDay), self.endHour, self.endMinute)
        
    def __str__(self):
        if self.startDay is None:
            return "%s:%s - %s:%s" %(str(self.startHour).zfill(2), str(self.startMinute).zfill(2), str(self.endHour).zfill(2), str(self.endMinute).zfill(2))

        weekDayNames = getWeekDayAbbreviations(lower=False)
        return "%s %s:%s - %s %s:%s" %(weekDayNames[self.startDay], str(self.startHour).zfill(2), str(self.startMinute).zfill(2), weekDayNames[self.endDay], str(self.endHour).zfill(2), str(self.endMinute).zfill(2))

class WeekRanges(list):
    '''
        WeekRanges - A list of WeekRange objects. Provides convienant means to check if a datetime intersects a series of ranges.

        The "createFromStr" method takes a comma-separated list of WeekRange strings (see #WeekRange for the formatting rules)

        The "intersects" method returns which WeekRange matched, or False if no match.

        Example:

            Check if during work hours:

            workHours = WeekRanges.createFromStr('Mon 09:00 - 18:00, Tue 09:00 - 18:00, Wed 09:00 - 18:00, Thu 09:00 - 18:00, Fri 09:00 - 18:00')
            isAtWork = workHours.intersect(datetime.datetime.now())

    '''

    @classmethod
    def createFromStr(cls, rangesStr, rangeClass=WeekRange):
        '''
            createFromStr - #see WeekRange.createFromStr. Creates a list of WeekRange (or whatever #rangeClass specifies) based off a comma-separated string.

            @param rangesStr <str> - comma-separated WeekRange strings (e.x. "Mon 09:00 - 18:00, Tue 09:00 - 18:00" )
            @param rangeClass <class> - Defauls to WeekRange, but if you extend WeekRange with your own special class you can specify it here to create instances of your alternative class.
        '''
        rangeStrs = [x.strip() for x in rangesStr.split(',')]
        ret = cls()

        for rangeStr in rangeStrs:
            if not rangeStr:
                continue
            ret.append(rangeClass.createFromStr(rangeStr))

        return ret

    def intersects(self, datetimeObj):
        '''
            intersects - Checks if the given datetime object intersects with any of the spans held within this object.

            @param datetimeObj <datetime.datetime> - The datetime object to check against

            @return <bool/WeekRange> - False if no intersections were found, otherwise returns the first range that matched. Will be of type WeekRange (or the alternate if you passed one to rangeClass in createFromStr)
        '''
        for weekRange in self:
            if weekRange.intersects(datetimeObj):
                return weekRange

        return False


class WeekRangeValueError(ValueError):
    '''
        WeekRangeValueError - Exception raised when there is an issue in the format of strings or other values passed to WeekRange methods.
    '''
    pass
