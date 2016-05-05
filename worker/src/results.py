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

import sqlite3


def get_elec(eplussql):
    return get_value(eplussql, "Electricity:Facility")

def get_non_elec(eplussql):
    return get_value(eplussql, "Gas:Facility")

def get_value(eplussql, name):
    with sqlite3.connect(eplussql) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT ReportDataDictionaryIndex
          FROM ReportDataDictionary 
          WHERE Name = '{}'
        """.format(name))
        try:
            index = c.fetchone()[0]
        except TypeError:
            return 0
        c.execute("""
        SELECT Value
          FROM ReportData
          WHERE ReportDataDictionaryIndex = '{}'
        """.format(index))
        value = c.fetchone()[0]
    conn.close()
    return value
    