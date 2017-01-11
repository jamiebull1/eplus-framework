# Copyright (c) 2016 Jamie Bull
# =======================================================================
#  Distributed under the MIT License.
#  (See accompanying file LICENSE or copy at
#  http://opensource.org/licenses/MIT)
# =======================================================================
"""pytest for schedules.py"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from geomeppy.utilities import almostequal

import pandas as pd
from worker.src.schedules import Schedule
from worker.src.schedules import activities_proportions
from worker.src.schedules import all_zone_schedules
from worker.src.schedules import all_zone_rates
from worker.src.schedules import area_weight_schedules
from worker.src.schedules import make_schedules


sch1_str = "Schedule:Year, C2_Edu_Circulation_Cool, , C2_Edu_Circulation_Cool_WK1, 1,1, 12,22, C2_Edu_Circulation_Cool_Wk2, 12,23, 1,9, C2_Edu_Circulation_Cool_WK1, 1,10, 2,13, C2_Edu_Circulation_Cool_Wk2, 2,14, 2,20, C2_Edu_Circulation_Cool_WK1, 2,21, 3,20, C2_Edu_Circulation_Cool_Wk2, 3,21, 4,3, C2_Edu_Circulation_Cool_WK1, 4,4, 5,29, C2_Edu_Circulation_Cool_Wk2, 5,30, 6,5, C2_Edu_Circulation_Cool_WK1, 6,6, 7,24, C2_Edu_Circulation_Cool_Wk2, 7,25, 9,4, C2_Edu_Circulation_Cool_Wk2, 9,5, 10,30, C2_Edu_Circulation_Cool_Wk2, 10,31, 12,31, C2_Edu_Circulation_Cool_WK1, 1,1, 10,23;Schedule:Week:Daily, C2_Edu_Circulation_Cool_Wk2, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Hol;Schedule:Week:Daily, C2_Edu_Circulation_Cool_WK1, C2_Edu_Circulation_Cool_Wknd, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wknd, C2_Edu_Circulation_Cool_Hol, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy, C2_Edu_Circulation_Cool_Wkdy;Schedule:Day:List, C2_Edu_Circulation_Cool_Hol, Cool, yes, 60, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100;Schedule:Day:List, C2_Edu_Circulation_Cool_Wkdy, Cool, yes, 60, 100, 100, 100, 100, 100, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 100, 100, 100, 100, 100;Schedule:Day:List, C2_Edu_Circulation_Cool_Wknd, Cool, yes, 60, 100, 100, 100, 100, 100, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 23.0, 100, 100, 100, 100, 100;"
sch2_str = "Schedule:Year, D1_Edu_DrySptHall_Cool, , D1_Edu_DrySptHall_Cool_Wk2, 1,1, 1,9, D1_Edu_DrySptHall_Cool_WK1, 1,10, 2,13, D1_Edu_DrySptHall_Cool_Wk2, 2,14, 2,20, D1_Edu_DrySptHall_Cool_WK1, 2,21, 3,20, D1_Edu_DrySptHall_Cool_Wk2, 3,21, 4,3, D1_Edu_DrySptHall_Cool_WK1, 4,4, 5,29, D1_Edu_DrySptHall_Cool_Wk2, 5,30, 6,5, D1_Edu_DrySptHall_Cool_WK1, 6,6, 7,24, D1_Edu_DrySptHall_Cool_Wk2, 7,25, 9,4, D1_Edu_DrySptHall_Cool_WK1, 9,5, 10,23, D1_Edu_DrySptHall_Cool_Wk2, 10,24, 10,30, D1_Edu_DrySptHall_Cool_WK1, 10,31, 12,22, D1_Edu_DrySptHall_Cool_Wk2, 12,23, 12,31;Schedule:Week:Daily, D1_Edu_DrySptHall_Cool_WK1, D1_Edu_DrySptHall_Cool_Wknd, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wknd, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy, D1_Edu_DrySptHall_Cool_Wkdy;Schedule:Week:Daily, D1_Edu_DrySptHall_Cool_Wk2, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol, D1_Edu_DrySptHall_Cool_Hol;Schedule:Day:List, D1_Edu_DrySptHall_Cool_Wkdy, Cool, yes, 60, 100, 100, 100, 100, 100, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 100, 100, 100, 100, 100;Schedule:Day:List, D1_Edu_DrySptHall_Cool_Wknd, Cool, yes, 60, 100, 100, 100, 100, 100, 100, 100, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 100, 100, 100, 100, 100, 100, 100, 100;Schedule:Day:List, D1_Edu_DrySptHall_Cool_Hol, Cool, yes, 60, 100, 100, 100, 100, 100, 100, 100, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 25.0, 100, 100, 100, 100, 100, 100, 100, 100;"


def test_combined_schedule():
    gifa = 1000
    schedule_types = ['Heat', 'Cool', 'Light', 'Equip', 'Occ']
    activities = activities_proportions(gifa)
    schedules = make_schedules(schedule_types, activities)

    return schedules

def test_area_proportions():
    gifa = 1000
    activities = activities_proportions(gifa)
    assert almostequal(sum(activities['area']), 1)


def test_real_schedules():
    schedule_types = ['Heat', 'Cool', 'Light', 'Equip', 'Occ']
    gifa = 1000
    activities = activities_proportions(gifa)
    zone_name = 'test'
    days_per_week = 5
    weeks_closed = 0
    occupancy_hours_scalar = 1
    all_zone_schedules(
        schedule_types, activities, zone_name, days_per_week, weeks_closed, 
        occupancy_hours_scalar)


def test_schedule():
    schedule_types = ['Heat', 'Cool', 'Light', 'Equip', 'Occ']
    activities = pd.DataFrame(
        [['Office', 1, 1],
         ['Teaching', 1, 1],
         ['Circulation', 1, 1],
         ['CommunalArea', 1, 1],
         ['EatDrink', 1, 1],
         ['Lecture', 1, 1],
         ['Reception', 1, 1],
         ['Toilet', 1, 1],
         ['FoodPrep', 1, 1],
         ['Storage', 1, 1],
         ['DrySportsHall', 1, 1],
         ],
        columns=['activity_code', 'area', 'final_line_area']
        )
    zone_name = 'test'
    days_per_week = 5
    weeks_closed = 0
    occupancy_hours_scalar = 1
    all_zone_schedules(
        schedule_types, activities, zone_name, days_per_week, weeks_closed, 
        occupancy_hours_scalar)


def test_rate():
    rate_types = ['Metab']
    activities = pd.DataFrame(
        [['Office', 1, 1],
         ['Teaching', 1, 1],
         ['Circulation', 1, 1],
         ['CommunalArea', 1, 1],
         ['EatDrink', 1, 1],
         ['Lecture', 1, 1],
         ['Reception', 1, 1],
         ['Toilet', 1, 1],
         ['FoodPrep', 1, 1],
         ['Storage', 1, 1],
         ['DrySportsHall', 1, 1],
         ],
        columns=['activity_code', 'area', 'final_line_area']
        )
    zone_name = 'test'
    rates = all_zone_rates(rate_types, activities, zone_name)
    print(rates)

def test_combine_schedule():
    sch1 = Schedule(sch1_str)
    sch2 = Schedule(sch2_str)
    sch3 = area_weight_schedules([sch1, sch2], [100, 100])
