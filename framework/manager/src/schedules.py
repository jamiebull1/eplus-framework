#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
schedules.py
~~~~~~~~~~~~
This module is used to create EnergyPlus schedules based on the NCM database.
It requires the NCM database to be available locally. It can be downloaded from
http://www.ncm.bre.co.uk/download.jsp.

The schedules are first made as Schedule:Year, Schedule:Week:Daily and
Schedule:Day:List objects. These are then parsed into 8760-hour annual
schedules which can be area weighted. The final schedules are saved as a CSV
file to be used by Schedule:File objects.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict, OrderedDict
import datetime
import itertools
import json
import logging
import os
import platform

from dateutil.rrule import rrule, DAILY
from six import StringIO
import sqlalchemy
from sqlalchemy.exc import DBAPIError

from geomeppy import IDF
from manager.src.config import config
import numpy as np
import pandas as pd


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
SCHEDULES_DIR = os.path.join(THIS_DIR, '../data/schedules')


DEFAULT_YEAR = 2015
pd.options.mode.chained_assignment = None


zones = {'teaching': {
            'activities': {
                'Teaching': {
                    'schedules': 'D1_Edu-ClassRm',
                    'rates': 'C2_Schools-Teaching',
                    'proportion': 1},
                },
            'area': {
                'm2': {'min': 0, 'max': 30},
                'm2_per_pupil': {'min': 2, 'max': 2.2},
                }
            },
        'halls_dining_pe': {
            'activities': {
                'Lecture': {
                    'schedules': 'D1_Edu-Lecture',
                    'rates': 'C2_Schools-Lecture',
                    'proportion': 1/3},
                'DrySportsHall': {
                    'schedules': 'D1_Edu-DrySptHall',
                    'rates': 'C2_Schools-DrySptHall',
                    'proportion': 1/3},
                'EatDrink': {
                    'schedules': 'C2_Schools-EatDrink',
                    'rates': 'C2_Schools-EatDrink',
                    'proportion': 1/3},
                },
            'area': {
                'm2': {'min': 100, 'max': 125},
                'm2_per_pupil': {'min': 0.3, 'max': 0.35},
                }
            },
        'learning_resources': {
            'activities': {
                'CommunalArea': {
                    'schedules': 'C2_Schools-CommunalArea',
                    'rates': 'C2_Schools-CommunalArea',
                    'proportion': 1},
                },
            'area': {
                'm2': {'min': 10, 'max': 30},
                'm2_per_pupil': {'min': 0.1, 'max': 0.2},
                }
            },
        'store': {
            'activities': {
                'Storage': {
                    'schedules': 'D1_Edu-Store',
                    'rates': 'C2_Schools-Store',
                    'proportion': 1},                                 
                },
            'area': {
                'm2': {'min': 20, 'max': 40},
                'm2_per_pupil': {'min': 0.15, 'max': 0.25},
                }
            },
        'staff_and_admin': {
            'activities': {
                'Reception': {
                    'schedules': 'D1_Edu-Reception',
                    'rates': 'C2_Schools-Reception',
                    'proportion': 1/2},                                 
                'Office': {
                    'schedules': 'D1_Edu-CellOff',
                    'rates': 'C2_Schools-Office',
                    'proportion': 1/2},
                },
            'area': {
                'm2': {'min': 30, 'max': 50},
                'm2_per_pupil': {'min': 0.2, 'max': 0.3},
                }
            },
        'non_net': {
            'activities': {
                'Toilet': {
                    'schedules': 'C2_Schools-Toilet',
                    'rates': 'C2_Schools-Toilet',
                    'proportion': 0.2},   
                'Circulation': {
                    'schedules': 'C2_Schools-Circulation',
                    'rates': 'C2_Schools-Circulation',
                    'proportion': 0.8},                                 
                },
            'area': {
                'm2': {'min': 110, 'max': 125},
                'm2_per_pupil': {'min': 1.2, 'max': 1.6},
                }
            },
        }


def activities_proportions(total_area):
    min_pupils = (total_area - 400) / 4.5
    max_pupils = (total_area - 350) / 4.1
    
    activities = {}
    for zone_type in zones:
        fixed = (zones[zone_type]['area']['m2']['min'],
                 zones[zone_type]['area']['m2']['max'])
        variable = (zones[zone_type]['area']['m2_per_pupil']['min'],
                    zones[zone_type]['area']['m2_per_pupil']['max'])
        lower = fixed[0] + min_pupils * variable[0]
        upper = fixed[1] + max_pupils * variable[1]
        zone_area = sum([lower, upper]) / 2
        #=======================================================================
        # zone_area = random.normalvariate(
        #     sum([upper, lower]) / 2,  # mu
        #     (upper - lower) / 2  # sigma
        #     )
        #=======================================================================
        for activity in zones[zone_type]['activities']:
            activity_dict = zones[zone_type]['activities'][activity]
            activities[activity] = zone_area * activity_dict['proportion']
    accounted_area = sum(activities[activity] for activity in activities)
    activities = {activity: [activity, 
                             activities[activity] / accounted_area, 
                             total_area
                             ]
                 for activity in activities}
    activities = pd.DataFrame.from_dict(activities, orient='index')
    activities.columns = ['activity_code', 'area', 'final_line_area']
    return activities


def make_schedules(zones, schedule_types, activities):
    all_schedules = {}
    for zone in zones:
        all_schedules[zone.Name] = {}
        for st in schedule_types:
            schedules = []
            areas = []
            for _i, row in activities.iterrows():
                activity = row['activity_code']
                area = row['area']
                f = os.path.join(SCHEDULES_DIR, '%s_%s.imf' % (activity, st))
                with open(f, 'rb') as schedule_file:
                    schedules.append(Schedule(schedule_file.read()))
                    areas.append(area)
            
            all_schedules[zone.Name][st] = area_weight_schedules(
                schedules, areas)
        
    return all_schedules


def make_rates(zones, rate_types, activities):
    all_rates = {}
    for zone in zones:
        all_rates[zone.Name] = {}
        for rt in rate_types:
            rates = []
            areas = []
            for _i, row in activities.iterrows():
                activity = row['activity_code']
                area = row['area']
                # need to get the rates for each activity from somewhere
                f = os.path.join(SCHEDULES_DIR, '%s_%s.imf' % (activity, rt))
                with open(f, 'rb') as rate_file:
                    rates.append(float(rate_file.read()) * area)
                    areas.append(area)
                areas.append(area)
            all_rates[zone.Name][rt] = sum(rates) / sum(areas)
        
    return all_rates


def area_weighted_rate(activities, rate):
    """Create an area-weighted composite rate from activity type rates.
    """
    sb = ScheduleBuilder()    
    rates = []
    for _i, row in activities.iterrows():
        code = row[0]
        area = row[1]
        rate_value = sb.generate_rate(code, rate)
        scaled_rate = rate_value * area
        rates.append(scaled_rate)
    averaged_rate = sum(rates) / activities['final_line_area'].sum()
    return averaged_rate


def all_zone_schedules(schedule_types, activities, zone_name, days_per_week, 
                       weeks_closed, occupancy_hours_scalar):
    """
    Create area weighted schedules for all activity zones.
    
    Parameters
    ----------
    schedule_types : list of strings
        Types of schedule required, e.g. 'Heat'.
    activities : list of dicts
       List of dictionaries containing activity code, floor number and area for 
       each activity type in a record.
    zone_name : str, int or float
        Floor number - must be able to be cast to an int.
    days_per_week : int
        Number of days operating per week. Used to set Saturday and Sunday
        schedules as weekdays if required.
    weeks_closed : int
        Number of weeks closed per year. Used to set an unoccupied holiday 
        period for the final weeks of the year.
    occupancy_hours_scalar : float
        Ratio by which to stretch or shrink the schedules.
    
    Returns
    -------
    dict
        Schedules generated.

    """
    zone_schedules = OrderedDict()
    for st in schedule_types:
        hourly = area_weighted_schedule(
            activities, st, occupancy_hours_scalar)
        if not hourly:
            continue
        if days_per_week >= 6:
            hourly = set_saturday_as_workday(hourly)
        if days_per_week == 7:
            hourly = set_sunday_as_workday(hourly)
        if st == 'Occ':
            hourly = set_closed_weeks(hourly, weeks_closed)
        
        zone_schedules['{0}_{1}'.format(zone_name, st)] = {'hourly': hourly}
            
    return zone_schedules


def set_closed_weeks(hourly, weeks_closed):
    """Set the final n weeks occupancy to zero.
    
    Parameters
    ----------
    hourly : list
        8760 hourly values.
    weeks_closed : int
        Number of weeks closed.
        
    Returns
    -------
    list
    
    """
    if weeks_closed > 0:
        num_hours_closed = weeks_closed * 24 * 7    
        hourly[-num_hours_closed:] = num_hours_closed * [0]
    
    return hourly


def set_saturday_as_workday(hourly):
    """Take the values from Friday and add them to Saturday.
    Parameters
    ----------
    hourly : list
        8760 hourly values.
        
    Returns
    -------
    list

    """
    df = pd.DataFrame(hourly, columns=['value'])
    df.index = pd.date_range(
        '2015-01-01','2016-01-01',
        freq='H')[:8760]
    df.loc[df.index.weekday==5] = df.shift(-24)
    
    return list(df['value'])


def set_sunday_as_workday(hourly):
    """Take the values from Friday and add them to Sunday.
    
    Parameters
    ----------
    hourly : list
        8760 hourly values.

    Returns
    -------
    list
    
    """
    df = pd.DataFrame(hourly, columns=['value'])
    df.index = pd.date_range(
        '2015-01-01','2016-01-01',
        freq='H')[:8760]
    df.loc[df.index.weekday==6] = df.shift(-24)
    
    return list(df['value'])


def area_weight_schedules(schedules, areas):
    """Area weight a group of schedules.
    
    Parameters
    ----------
    schedules : list
        A list of schedules in hourly list format.
    areas : list
        A list of areas corresponding to each schedule.
    
    Returns
    -------
    list
    
    """
    total_area = sum(areas)
    summed_schedule = [0] * len(schedules[0].hourly_schedule)
    for schedule, area in zip(schedules, areas):
        schedule = [i * area for i in schedule.hourly_schedule]
        summed_schedule = [a + b for a, b in zip(summed_schedule, schedule)]
    area_weighted = [i / total_area for i in summed_schedule]
    return area_weighted


def all_zone_rates(rate_types, activities, zone):
    """
    Create area weighted schedules for all activity zones.
    
    Parameters
    ----------
    rate_types : list of strings
        Types of rate required, e.g. 'Metab'.
    activities : list of dicts
       List of dictionaries containing activity code, floor number and area for 
       each activity type in a record.
    
    Returns
    -------
    dict
        Rates generated.

    """
    zone_rates = OrderedDict()
    for rate in rate_types:
        average_rate = area_weighted_rate(activities, rate)
        zone_rates['Zone{0}{1}'.format(zone, rate)] = average_rate
            
    return zone_rates


class ScheduleBuilder(object):
    """
    Class to handle database access and generation of EnergyPlus schedules.
    Replace the values for SERVER, DB_NAME and DRIVER before running. These
    should probably be moved into a config file so we can each have our own
    versions.
    
    """
    if platform.system() == 'Windows':
        SERVER = config.get('ScheduleDB', 'server')
        DB_NAME = config.get('ScheduleDB', 'db_name')
        DRIVER = config.get('ScheduleDB', 'driver')
        conn_string = "{SERVER}/{DB_NAME}?driver={DRIVER}".format(**locals())
        tablepattern = '[{self.DB_NAME}].[dbo].[{table}]'
    else:
        SERVER = 'mysql'
        DB_NAME = 'NCM'
        DRIVER = ''
        conn_string = "mysql://root:@localhost:3306"
        tablepattern = '{self.DB_NAME}.{table}'

    dir = os.path.join(THIS_DIR, 'schedules')
        
    def __init__(self):
        self.engine = sqlalchemy.create_engine(self.conn_string, echo=False)
        try:
            self.engine.connect()
        except DBAPIError:
            raise Exception('Building schedules requires the NCM database. \
It can be downloaded from http://www.ncm.bre.co.uk/download.jsp. \
If you already have the database, then check SERVER, DB_NAME and \
DRIVER parameters for the schedules.ScheduleBuilder object')
        
    def set_dir(self, working_dir):
        self.dir = working_dir
    
    def generate_schedules(self, activity_codes, schedules):
        """
        Write all requested schedules to an IMF file which can be included in
        another IMF file.
        
        Parameters
        ----------
        activity_codes : list of str
            The activity codes to for which schedules are required.
        schedules : list of str
            List of the type of schedules required.
            
        Example
        -------
        >>> generate_schedules(['CO.OFF', 'CO.KTN'], ['Heat', 'Light'])
                              
        """
        for code, schedule in itertools.product(activity_codes, schedules):
            self.generate_schedule(code, schedule)
    
    def generate_schedule(self, code, schedule):
        """
        Generate a single schedule.
        
        Parameters
        ----------
        code : str
            Activity name.
        schedule : str
            Type of schedule required, e.g. 'Heat'.
        
        Returns
        -------
        str
            The requested schedule in IDF format.
            
        """
        code = map_code_to_NCM_activity(code)
        imf = '%s_%s.imf' % (code['given_code'], schedule)
        imf_path = os.path.join(self.dir, imf)
        try:
            with open(imf_path) as schedule_file:
                schedule_str = schedule_file.read()
        except IOError:
            try:
                building_type, zone = code['schedule_code'].split('-')
            except ValueError:
                # logger.error(code['schedule_code'])
                raise
            try:
                schedule_str = self.create_schedule(
                    building_type, zone, schedule)
            except KeyError:
                raise
            with open(os.path.join(SCHEDULES_DIR, imf), 'wb') as f_out:
                f_out.write(schedule_str)
        return schedule_str

    def generate_rates(self, activity_codes, rates):
        """
        Write all requested rates to an IMF file which can be included in
        another IMF file. This is currently used for metabolic rate.
        
        Parameters
        ----------
        activity_codes : str
            The activity codes to for which schedules are required.
        rates : list of str
            List of the type of rates required.
            
        Example
        -------
        >>> generate_rates(['CO.OFF', 'CO.KTN'], ['Metab'])
                              
        """
        for code, rate in itertools.product(activity_codes, rates):
            self.generate_rate(code, rate)
    
    def generate_rate(self, code, rate):
        """
        Generate a single rate schedule.
        
        Parameters
        ----------
        code : dict
            A dict containing the various versions of activity code.
        rate : str
            Type of rate required, e.g. 'Metab'.
        
        Returns
        -------
        str
            The requested rate schedule in IDF format.
            
        """
        code = map_code_to_NCM_activity(code)
        imf = '%s_%s.imf' % (code['given_code'], rate)
        imf_path = os.path.join(self.dir, imf)
        try:
            with open(imf_path) as rate_file:
                rate_value = rate_file.read()
        except IOError:
            try:
                building_type, zone = code['rate_code'].split('-')
            except ValueError:
                # logger.error(code['rate_code'])
                raise
            try:
                rate_value = self.create_rate_schedule(
                    building_type, zone, rate)
                with open(os.path.join(SCHEDULES_DIR, imf), 'wb') as f_out:
                    f_out.write(str(rate_value))
            except KeyError:
                raise
            except IndexError:
                raise

        return rate_value

    def select(self, table, fields=None, where=None, first=False):
        """Query data in database.
    
        Parameters
        ----------
        table : str
            Table name, or any other valid source of a rowset.
        fields : str, optional
            A valid SQL expression to select fields.
        where : str, optional
            A valid SQL expression to select rows (without the WHERE keyword).
    
        Returns
        -------
            pd DataFrame object
    
        """
        tablename = self.tablepattern.format(**locals())
        fields = "{fields}".format(**locals()) if fields else '*'
    
        select = "SELECT {fields} FROM {tablename}".format(**locals())
        where = "WHERE {where}".format(**locals()) if where else ''
        sql = "{select} {where}".format(**locals())
    
        return pd.read_sql(sql, self.engine)

    def create_schedule(self, building_type, zone, schedule):
        """
        Return a full EnergyPlus schedule set including a Schedule:Year, its
        referenced Schedule:Week:Daily schedules and their referenced
        Schedule:Daily schedules.
    
        Parameters
        ----------
        building_type : str
            The building type, e.g. Office
        zone : str
            The zone type, e.g. OpenOffice, Circulation.
        schedule : str
            The type of schedule, e.g. Heat, Occ.
    
        Returns
        -------
        str
            A formatted string containing all of the schedules.
    
        """
        annual_id = self.get_annual_id(building_type, zone, schedule)
        annual_weekly_schedules = self.get_annual_weekly_schedule(annual_id)
        annual = self.make_schedule_year(annual_weekly_schedules)
        
        weekly_ids = annual_weekly_schedules['WEEKLY_SCHEDULE'].unique()
        weekly_schedules = {w_id: self.make_schedule_week_daily(w_id)
                            for w_id in weekly_ids}
        
        daily_ids = self.get_daily_ids(weekly_ids)
        daily_schedules = {d_id: self.get_daily_schedule(d_id) for d_id in daily_ids}
    
        weekly = "\n\n".join([weekly_schedules[w] for w in weekly_schedules])
        daily = "\n\n".join([daily_schedules[d] for d in daily_schedules])
        joined_schedules = "{annual}\n\n{weekly}\n\n{daily}\n\n".format(**locals())
    
        return joined_schedules

    def get_annual_id(self, building_type, zone, schedule):
        """Get the ID number of an annual schedule.
        """
        annual_id = self.select(
            'annual_schedules',
            where="NAME='{building_type}_{zone}_{schedule}'".format(**locals())
        )['ID']
        try:
            return int(annual_id)
        except TypeError:
            raise KeyError('Annual ID not found')
        
    def get_annual_weekly_schedule(self, annual_id):
        """
        Fetch records which tells us in which weeks of the year each weekly
        schedule should be applied.

        """
        annual_weekly_schedule = self.select(
            'annual_weekly_schedules',
            where="ANNUAL_SCHEDULE='{annual_id}'".format(**locals())
        )
        return annual_weekly_schedule
    
    def make_schedule_year(self, aws):
        """Build the Schedule:Year object from the annual weekly schedule.
        """
        # create the header part of the schedule
        obj_type = "Schedule:Year"
        name = self.select(
            'annual_schedules',
            where="ID='%s'" % aws['ANNUAL_SCHEDULE'].iloc[0]
        ).iloc[0]['NAME']
        type_limits = ""  # not currently used
        header = "{obj_type},\n\t{name},\n\t{type_limits}".format(**locals())

        # create the dates part of the schedule
        aws = self.add_start_dates(aws)
        dates = []
        for i in range(len(aws)):
            row = aws.iloc[i]
            week_name = self.select(
                'weekly_schedules',
                where="ID='%s'" % aws.iloc[i]['WEEKLY_SCHEDULE']
            ).iloc[0]['NAME']
            start_date = "%s,%s" % (row['START_MONTH'], row['START_DAY'])
            end_date = "%s,%s" % (row['END_MONTH'], row['END_DAY'])
            dates += ["{week_name}, {start_date}, {end_date}".format(**locals())]
        dates = ",\n\t".join(dates)
        
        # join the header and dates
        schedule_year = "{header},\n\t{dates};".format(**locals())

        return schedule_year

    def add_start_dates(self, aws):
        """
        Set new columns for START_DAY and START_MONTH. The start dates are set one
        day later than the end dates in the previous row and the first row has
        START_DAY and START_MONTH both set to 1 (e.g. Jan 1st).
    
        Parameter
        ---------
        aws : pd DataFrame
            An extract from the NCM annual_weekly_shedules table.
    
        Returns
        -------
        pd.DataFrame
            The same table with start day, date and month columns added.
    
        """
        aws['YEAR'] = 2000
        month_num = lambda x: datetime.datetime.strptime(x, '%b').month
        aws['END_MONTH'] = aws['END_MONTH'].apply(month_num)
        aws['END_DAY'] = aws['END_DAY'].astype(np.int64)
    
        aws['END_DATE'] = pd.to_datetime((aws['YEAR'] * 10000 +
                                              aws['END_MONTH'] * 100 +
                                              aws['END_DAY']).astype(str),
                                             format="%Y%m%d")
        aws['START_DATE'] = aws['END_DATE'] + datetime.timedelta(days=1)
        aws['START_DATE'] = aws['START_DATE'].shift(1)
        aws['START_DATE'][0] = datetime.datetime(DEFAULT_YEAR, 1, 1)
        aws['START_DAY'] = aws['START_DATE'].apply(lambda x: x.day)
        aws['START_MONTH'] = aws['START_DATE'].apply(lambda x: x.month)
    
        return aws

    def make_schedule_week_daily(self, w_id):
        """
        Build a Schedule:Week:Daily object from the weekly schedule. The days
        are in the order:            
        
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
        "Holiday",
        "SummerDesignDay", "WinterDesignDay",
        "CustomDay1", "CustomDay2"
                 
        """
        obj_type = "Schedule:Week:Daily"
        sch = self.select('weekly_schedules',
            where="ID='%s'" % w_id)
        name = sch['NAME'].iloc[0]
        week_sch = [sch['SUNDAY'], sch['MONDAY'], sch['TUESDAY'], sch['WEDNESDAY'],
                    sch['THURSDAY'], sch['FRIDAY'], sch['SATURDAY'],
                    sch['HOLIDAY'],
                    sch['MONDAY'], sch['MONDAY'],
                    sch['MONDAY'], sch['MONDAY']]
        week_sch = [self.get_day_name(d) for d in week_sch]
        week_sch = ",\n\t".join([str(d) for d in week_sch])
    
        return "{obj_type},\n\t{name},\n\t{week_sch};".format(**locals())

    def get_day_name(self, day):
        name = self.select(
            'daily_schedules',
            fields='NAME',
            where="ID='%s'" % int(day)
        ).iloc[0].iloc[0]
        return name

    def get_daily_ids(self, weekly_ids):
        """Returns the set of daily schedule IDs referenced by a set of weekly IDs.
    
        Parameter
        ---------
        weekly_ids : numpy.ndarray
            An array of weekly ID numbers.
    
        Returns
        -------
        list
            A list of ints
    
        """
        days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY',
                'FRIDAY', 'SATURDAY', 'SUNDAY', 'HOLIDAY']
        daily_ids = []
        for w_id in weekly_ids:
            sch = self.select('weekly_schedules',
                fields=",".join(days),
                where="ID='%s'" % w_id)
            daily_ids += list(sch.iloc[0].astype(int))
        return list(set(daily_ids))

    def get_daily_schedule(self, daily_id):
        """Return a formatted EnergyPlus Schedule:Day:List.
    
        Parameters
        ----------
        daily_id : int
    
        Returns
        -------
        str
    
        """
        schedule = self.select(
            'daily_schedules',
            where="ID='{daily_id}'".format(**locals())
        )
        schedule_obj = self.make_schedule_day_list(schedule)
        return schedule_obj
    
    def get_daily_schedule_eppy(self, daily_id):
        """Return a formatted EnergyPlus Schedule:Day:Interval created using Eppy.
    
        Parameters
        ----------
        daily_id : int
    
        Returns
        -------
        str
    
        """
        schedule = self.select(
            'daily_schedules',
            where="ID='{daily_id}'".format(**locals())
        )
        off_vals = {'Cool': '100',
                     'Heat': '-100'}
        name = schedule['NAME'][0]
        s_type = name.split('_')[-2]
        time_cols = [col for col in schedule if
                     col.startswith('h') and
                     col != 'holiday']
        values = list(schedule[time_cols].iloc[0].astype(str))
        values = [v if v != 'None' else off_vals[s_type] for v in values]
        
        fhandle = StringIO("")
        idf = IDF(fhandle)
        sch = idf.newidfobject(
            'SCHEDULE:DAY:INTERVAL',
            Name=name,
            Schedule_Type_Limits_Name=s_type,
            Interpolate_to_Timestep='Yes',
            )
        t = 1
        for i, v in enumerate(values):
            if i == 0:
                continue
            if values[i-1] != v:
                sch['Time_%s' % t] = 'Until: %i:00' % i 
                sch['Value_Until_Time_%s' % t] = values[i-1]
                t += 1
                    
            if i == 23:
                sch['Time_%s' % t] = 'Until: 24:00'
                sch['Value_Until_Time_%s' % t] = v

        schedule_obj = str(sch) # = self.make_schedule_day_list(schedul

        return schedule_obj
    
    def make_schedule_day_list(self, schedule):
        """Build a Schedule:Day:List object from a daily schedule.
        """
        off_vals = {'Cool': '100',
                     'Heat': '-100'}
        obj_type = "Schedule:Day:List"
        name = schedule['NAME'][0]
        s_type = name.split('_')[-2]
        fill = 'yes'
        mins = 60
        time_cols = [col for col in schedule if
                     col.startswith('h') and
                     col != 'holiday']
        
        
        header = "{obj_type},\n\t{name},\n\t{s_type},\n\t{fill}".format(
            **locals())
        values = list(schedule[time_cols].iloc[0].astype(float))
        values = self.scale_values(values)
        values = [v if v != 'nan' else off_vals[s_type] for v in values]

        values = ',\n\t'.join(values)
        return "{header},\n\t{mins},\n\t{values};".format(**locals())

    def scale_values(self, values):
        """
        Spread out the values to fill a larger proportion of the day if the
        building is occupied for more of the day than usual. We assume that
        the working day is centred around 12pm and that extra hours are evenly
        split between the start and end of the day.       
        
        Parameters
        ----------
        values : list
            List of schedule values for a day.
            
        """
        scalar = self.occupancy_hours_scalar
        values = stretch(values, scalar, 12)
        values = [str(v) for v in values]
        return values
        
    def create_rate_schedule(self, building_type, zone, rate):
        """
        Return activity schedules which are constant values so can be defined as
        Schedule:Compact objects in EnergyPlus.
    
        Parameters
        ----------
        building_type : str
            The building type, e.g. Office
        zone : str
            The zone type, e.g. OpenOffice, Circulation.
        rate : str
            The type of rate, e.g. Metab.
    
        Returns
        -------
        str
            A formatted EnergyPlus schedule.
    
        """
        rate_col = map_rate_to_NCM_column(rate)
        rate_value = self.select(
            'activity',
            where="NAME='{building_type}_{zone}'".format(**locals())
        )
        rate_value = rate_value[rate_col]
        rate_value = rate_value.iloc[0]
        rate_value = float(rate_value)

        return rate_value


def map_code_to_NCM_activity(activity_code):
    """
    This function is needed to map from an activity code in the given format to
    ones that can be found in the NCM database.
    
    For now we have a deterministic mapping stored in a dict, but this should
    eventually be expanded/completed and moved into a json file.
    
    Parameters
    ----------
    activity_code : str
        Activity code from given data.
    
    Returns
    -------
    tuple of str
        (Building type, zone type).
        
    """
    with open(os.path.join(SCHEDULES_DIR, 'mapToNCM.json'), 'rb') as data:
        activity_map = {item.keys()[0]: item for item in json.loads(data.read())}
    
    mapped_activity = activity_map[activity_code][activity_code]

    return mapped_activity

def map_rate_to_NCM_column(rate):
    """
    This function is needed to map from a rate name to a column in the
    'activities' table in the NCM database.
    
    """
    rate_map = {'Metab': 'METABOLIC_RATE'}
    return rate_map[rate]

def get_external_temps(epw):
    """
    Find the outdoor temperature for the current location.
    
    Parameters
    ----------
    epw : str
        Path to the EnergyPlus weather file.
    
    Returns
    -------
    list
        Hourly (8760 hours) outdoor temperature.
    
    """
    epw_headers = [
        'year', 'month', 'day', 'hour', 'minute', 'datasource', 'drybulb',
        'dewpoint', 'relhum', 'atmos_pressure', 'exthorrad', 'extdirrad',
        'horirsky', 'glohorrad', 'dirnorrad', 'difhorrad', 'glohorillum',
        'dirnorillum', 'difhorillum', 'zenlum', 'winddir', 'windspd',
        'totskycvr', 'opaqskycvr', 'visibility', 'ceiling_hgt',
        'presweathobs', 'presweathcodes', 'precip_wtr',
        'aerosol_opt_depth', 'snowdepth', 'days_last_snow', 'Albedo', 
        'liq_precip_depth', 'liq_precip_rate']
    data = pd.read_csv(epw, skiprows=8, header=None, names=epw_headers)
    external_temps = list(data['drybulb'])

    return external_temps


def area_weighted_schedule(activities, st, occupancy_hours_scalar):
    """Create an area-weighted composite schedule from activity type schedules.
    """
    sb = ScheduleBuilder()
    sb.occupancy_hours_scalar = occupancy_hours_scalar
    hourly_schedules = []
    for _i, row in activities.iterrows():
        code = row[0]
        area = row[1]
        if not code:
            return
        schedule_str = sb.generate_schedule(code, st)
        s = Schedule(schedule_str)
        # convert to numpy array for faster processing and simpler operations
        np_schedule = np.array(s.hourly_schedule)
        if st.lower() == 'heat':
            # replace -100 values with 0
            np_schedule[np_schedule < 0] = 0
        scaled_schedule = np_schedule * area
        hourly_schedules.append(scaled_schedule)
    
    hourly_schedules = np.array(hourly_schedules)
    averaged_schedule = (
        np.sum(hourly_schedules, axis=0) / activities['final_line_area'].sum())
    # convert back to list as np arrays can't be serialised to JSON    
    averaged_schedule = list(averaged_schedule)
    return averaged_schedule


class Schedule(object):

    
    def __init__(self, schedule_str):
        """Read EnergyPlus schedules and convert to 8760 hours of hourly values.
        
        Parameters
        ----------
        schedule_str : str
            A complete set of schedules in EnergyPlus format. These must be in
            Schedule:Year, Schedule:Week:Daily and Schedule:Day:List format.
        
        """
        self.input = schedule_str
        self.objects = defaultdict(list)
        self.parse_schedule()
        
    def parse_schedule(self):
        """Parse the schedule string into year, week and day objects.
        """
        objects = self.input.split(';')
        objects = [[field.strip() for field in obj.split(',')] for obj in objects]
        self.years = {obj[1]: Year(obj) for obj in objects
                     if obj[0] == 'Schedule:Year'}
        self.weeks = {obj[1]: Week(obj) for obj in objects
                     if obj[0] == 'Schedule:Week:Daily'}
        self.days = {obj[1]: Day(obj) for obj in objects
                     if obj[0] == 'Schedule:Day:List'}
    
    @property
    def hourly_schedule(self):
        """8760-hour hourly schedule or schedules.
        
        Returns
        -------
        list
            
        """
        day_list = ['Monday','Tuesday','Wednesday','Thursday','Friday',
                    'Saturday','Sunday'
                    ]
        year_of_hours = ['n/a'] * 8760  # initialise with a flag value of n/a
        for y in self.years:
            # for each period
            for p in self.years[y].periods:
                a = self.years[y].periods[p]['start']
                b = self.years[y].periods[p]['end']
                # step through the period one day at a time
                for dt in rrule(DAILY, dtstart=a, until=b):
                    day_of_year = dt.timetuple().tm_yday
                    # look up the day type
                    days = self.weeks[p.split('#')[0]].days
                    d = day_list[dt.weekday()]
                    # store the value for each hour in the period
                    for i, h_val in enumerate(self.days[days[d]].hourly_values):
                        hour_num = (day_of_year - 1) * 24 + i
                        year_of_hours[hour_num] = float(h_val)
        return year_of_hours
        
        
class Year(object):
    
    def __init__(self, inputs):
        # parse the schedule header
        self.schedule_type = inputs[0]
        self.name = inputs[1]
        self.type_limits = inputs[2]
        # parse the field sets into periods 
        self.periods = defaultdict(dict)
        field_sets = list(chunks(inputs[3:], 5))
        for i, fs in enumerate(field_sets):
            start_date = datetime.date(DEFAULT_YEAR, int(fs[1]), int(fs[2]))
            end_date = datetime.date(DEFAULT_YEAR, int(fs[3]), int(fs[4]))
            self.periods['{0}#{1}'.format(fs[0], i)] = {'start': start_date,
                                                        'end': end_date}
    

class Week(object):
    
    day_types = [
                 "Sunday", "Monday", "Tuesday", "Wednesday",
                 "Thursday", "Friday", "Saturday",
                 "Holiday",
                 "SummerDesignDay", "WinterDesignDay",
                 "CustomDay1", "CustomDay2"
                 ]

    def __init__(self, inputs):
        # parse the schedule header
        self.schedule_type = inputs[0]
        self.name = inputs[1]
        # map day types to day names 
        self.days = {dt: obj_type for dt, obj_type
                     in zip(self.day_types, inputs[2:])}


class Day(object):
    
    def __init__(self, inputs):
        # parse the schedule header
        self.schedule_type = inputs[0]
        self.name = inputs[1]
        self.type_limits = inputs[2]
        self.interpolate_to_timestep = inputs[3]
        self.minutes_per_item = inputs[4]
        # parse the values
        self.hourly_values = inputs[5:]


def stretch(xs, coef, centre):
    """Scale a list by a coefficient around a point in the list.
    
    Parameters
    ----------
    xs : list
        Input values.
    coef : float
        Coefficient to scale by.
    centre : int
        Position in the list to use as a centre point.
    
    Returns
    -------
    list
    
    """
    if coef == 0:
        return xs
    grain = 100
    stretched_xs = []
    days = chunks(xs, 24)
    for xs in days:
        stretched_array = np.repeat(xs, grain * coef)
        
        if coef < 1:
            # pad start and end
            total_pad_len = grain * len(xs) - len(stretched_array)
            centre_pos = float(centre) / len(xs)
            start_pad_len = centre_pos * total_pad_len
            end_pad_len = (1 - centre_pos) * total_pad_len
            start_pad = [stretched_array[0]] * int(start_pad_len)
            end_pad = [stretched_array[-1]] * int(end_pad_len)
            stretched_array = np.array(start_pad + list(stretched_array) + end_pad)
        else:
            pivot_point = (len(xs) - centre) * grain * coef
            first = int(pivot_point - (len(xs) * grain) / 2)
            last = first + len(xs) * grain
            stretched_array = stretched_array[first:last]
        
        stretched_xs.extend(
            [round(chunk.mean(), 2) 
             for chunk in chunks(stretched_array, grain)])
    return stretched_xs


def chunks(iterable, n):
    """
    Yield successive n-sized chunks from iterable.
    Source: http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python#answer-312464

    """
    for i in xrange(0, len(iterable), n):
        yield iterable[i:i + n]
