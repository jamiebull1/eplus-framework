# Copyright (c) 2016 Jamie Bull
# =======================================================================
#  Distributed under the MIT License.
#  (See accompanying file LICENSE or copy at
#  http://opensource.org/licenses/MIT)
# =======================================================================
"""
Class to add the ability to run IDF objects in EnergyPlus directly from Eppy.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import pydoc

from src.run_functions import run, IDF

#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)


def wrapped_help_text(wrapped_func):
    """Decorator to pass through the documentation from a wrapped function.
    """
    def decorator(wrapper_func):
        """The decorator.

        Parameters
        ----------
        f : callable
            The wrapped function.

        """
        wrapper_func.__doc__ = ('This method wraps the following method:\n\n' +
                                pydoc.text.document(wrapped_func))
        return wrapper_func
    return decorator


class RunnableIDF(IDF):

    """Subclass of IDF used to carry out simulation runs.
    """

    def __init__(self, idf, epw):
        """
        Parameters
        ----------
        idf : file or file-like object
            The IDF object to run.
        epw : str
            File path to the EPW file to use.

        """
        logging.debug("{}, {}".format(idf, epw))
        super(RunnableIDF, self).__init__(idf)
        self.epw = epw
        logging.debug("Initialised RunnableIDF")
        
    @wrapped_help_text(run)
    def run(self, **kwargs):
        """
        Run an IDF file with a given EnergyPlus weather file. This is a
        wrapper for the EnergyPlus command line interface.

        Parameters
        ----------
        **kwargs
            See eppy.runner.functions.run()

        """
        # write the IDF to the current directory
        self.saveas('in.idf')
        # run EnergyPlus
        run('in.idf', self.epw, **kwargs)
        # remove in.idf
        #=======================================================================
        # with open('in.idf', 'rb') as f:
        #     logging.info(f.read())
        #=======================================================================
        os.remove('in.idf')
