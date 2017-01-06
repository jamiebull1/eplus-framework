#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Handles access to the config file.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import ConfigParser
import os


THIS_DIR = os.path.abspath(os.path.dirname(__file__))

config = ConfigParser.SafeConfigParser()
config.readfp(open(os.path.join(THIS_DIR, os.pardir, 'data/client.cfg')))
