"""
idfsyntax.py
~~~~~~~~~~~~
Module to convert an idf based on the job parameters passed in.

"""
import logging

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

def prepare_idf(idf, job):
    logging.debug("Editing IDF")
    for key, value in job:
        logging.debug("{}: {}".format(key, value))
    return idf
