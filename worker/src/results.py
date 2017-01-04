#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
results.py
~~~~~~~~~~
Module for the extraction of results from EnergyPlus SQLite output files.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import re
import sqlite3


JOULES_PER_KWH = 3600000


def get_elec(eplussql):
    elec_joules = get_value(eplussql, "Electricity:Facility")
    elec = elec_joules / JOULES_PER_KWH
    logging.debug('Electricity: %.2f' % elec)
    return elec


def get_non_elec(eplussql):
    gas_joules = get_value(eplussql, "Gas:Facility")
    gas = gas_joules / JOULES_PER_KWH
    logging.debug('Gas: %.2f' % gas)
    district_heat_joules = get_value(eplussql, "DistrictHeating:Facility")
    district_heat = district_heat_joules / JOULES_PER_KWH
    logging.debug('District Heat: %.2f' % district_heat)
    return gas + district_heat


def get_execution_time(eplusend):
    """Get the execution time in seconds.
    
    Parameters
    ----------
    eplusend : str
        Path to the .end file.
    
    Returns
    -------
    float
    
    """
    with open(eplusend, 'r') as f:
        text = f.read()
    time = text.split(';')[-1]
    h, m, s, ms = [int(n) for n in re.findall('\d+', time)]
    secs = (h * 60 * 60 +
            m * 60 +
            s +
            ms / 100.0)

    return secs
    

def get_value(eplussql, name):
    try:
        with sqlite3.connect(eplussql) as conn:
            c = conn.cursor()
            c.execute("""
    SELECT Value FROM ReportDataDictionary as rdd
    JOIN ReportData as rd
        ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
    WHERE Name = '{}' 
        AND ReportingFrequency = 'Run Period'
                """.format(name))
            value = float(c.fetchone()[0])
    except TypeError:
        logging.debug("Failed getting %s" % name)
        value = 0
    return value
    