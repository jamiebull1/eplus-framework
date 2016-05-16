"""
sampler.py
~~~~~~~~~~

Generate samples from an input file.

"""
from SALib.analyze import sobol
from SALib.sample import saltelli
from SALib.util import read_param_file
import numpy as np


def evaluate_model(X):
    print zip(problem['names'], X)
    return X

problem = read_param_file('/client/data/parameters.txt')

def samples():
    """Sample parameter values and return a generator of jobs.
    """
    runs = saltelli.sample(problem, 3, calc_second_order=True)
    as_floats = enumerate(zip(problem['names'], (float(n) for n in run)) 
                 for run in runs)
    empty_results = np.nan * np.empty(len(runs))
    return as_floats, empty_results


def analyse(Y):
    Si = sobol.analyze(problem, Y, print_to_console=True, calc_second_order=True)
