"""
sensitivity.py
~~~~~~~~~~~~~~

Generate samples from an input file, run sensitivity analysis, process the
results, and save the results to file.

This module uses SALib to conduct the sensitivity analysis.

To use, the variables should be listed in /client/data/parameters.txt and then
worker.idfsyntax.py should be edited to use the parameters to build an IDF.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import Queue
from copy import deepcopy
import json
import logging
import time

from SALib.analyze import morris as analyse_morris
from SALib.analyze import sobol
from SALib.sample import morris as sample_morris
from SALib.sample import saltelli
from SALib.util import read_param_file
import numpy as np


#from SALib.analyze.morris import compute_grouped_metric
#from SALib.analyze.morris import compute_grouped_sigma
J_per_kWh = 3600000

problem = read_param_file('/client/data/parameters.txt')
#schools = 


def sensitivity_analysis(
        job_q, result_q, sample_method, analysis_method, N, *args, **kwargs):
    """Conduct sensitivity analysis.
    """
    names, runs, empty_results = samples(sample_method, N=N, *args, **kwargs)
    jobs = enumerate(zip(names, (float(n) for n in run)) for run in runs)
    with open('/client/data/schools.json', 'r') as f:
        schools = json.load(f)
    school = schools.popitem()

    logging.debug("Initialising empty results")
    elec_results = deepcopy(empty_results)
    nonelec_results = deepcopy(empty_results)
    time_results = deepcopy(empty_results)

    step = 5 # percent complete
    last_step = 0
    t0 = time.time()
    while np.isnan(elec_results).any():
        try:
            job = make_job_json(*jobs.next(), school=school)
            job_q.put(job)
        except (Queue.Empty, StopIteration) as e:
            pass
        try:
            result = result_q.get_nowait()
            elec_results[result['id']] = result['electrical'] / J_per_kWh
            nonelec_results[result['id']] = result['non-electrical'] / J_per_kWh
            time_results[result['id']] = result['time']
            done = (float(result['id']) + 1) / len(elec_results) * 100
            if done > last_step + step:
                last_step += step
                update_log(t0, done)
        except (Queue.Empty, StopIteration) as e:
            pass
    job_q.put('kill worker')
    logging.info("Analysing results")
    analyse(
        runs, elec_results, 'elec.txt', method=analysis_method, *args, **kwargs)
    analyse(
        runs, nonelec_results, 'nonelec.txt', method=analysis_method, *args, **kwargs)
    analyse(
        runs, time_results, 'time.txt', method=analysis_method, *args, **kwargs)


def update_log(t0, done):
    logging.info("%.2f%% done" % done)
    t1 = time.time()
    secs = t1 - t0
    remaining = 100 - done
    secs_per_percent = secs / done
    secs_remaining = secs_per_percent * remaining
    logging.info("Approx %.1f mins remaining" % (secs_remaining / 60))


def make_job_json(i, sample, school):
    job = {'job': {'id': i, 
                   'school': school,
                   'params': {key: value for key, value in sample}}}
    return json.dumps(job)


def evaluate_model(X):
    print(zip(problem['names'], X))
    return X


def samples(method='morris', N=1, *args, **kwargs):
    """Sample parameter values and return a generator of jobs.
    """
    if method == 'morris':
        runs = sample_morris.sample(problem, N, *args, **kwargs)
    elif method == 'saltelli':
        second_order = kwargs['second_order']
        logging.info("Calculate second order effects: %s" % second_order)
        runs = saltelli.sample(problem, N, calc_second_order=second_order)
    else:
        logging.error("%s is not a valid sample method" % method)
        raise TypeError("%s is not a valid sample method" % method)
    logging.info("Creating %i jobs" % len(runs))
    empty_results = np.nan * np.empty(len(runs))

    return problem['names'], runs, empty_results


def analyse(X, Y, filename=None, method='morris', groups=None, *args, **kwargs):
    if method == 'morris':
        Si = analyse_morris.analyze(problem, X, Y)
    if method == 'sobol':
        second_order = kwargs['second_order']
        Si = sobol.analyze(problem, Y, calc_second_order=second_order)
    # write results
    if filename:
        second_order = kwargs['second_order']
        write_results(filename, Si, problem, method=method, groups=groups, 
                      calc_second_order=second_order)


def write_results(filename, Si, problem, method, groups, calc_second_order):
    if method == 'morris':
        num_vars = problem['num_vars']
        with open('/tmp/results/%s' % filename, 'w') as f:
            # Output to file
            if groups is None:
                f.write("{0:<30} {1:>10} {2:>10} {3:>15} {4:>10}\n".format(
                                    "Parameter",
                                    "Mu_Star",
                                    "Mu",
                                    "Mu_Star_Conf",
                                    "Sigma")
                      )
                for j in list(range(num_vars)):
                    f.write("{0:30} {1:10.3f} {2:10.3f} {3:15.3f} {4:10.3f}\n".format(
                                        Si['names'][j],
                                        Si['mu_star'][j],
                                        Si['mu'][j],
                                        Si['mu_star_conf'][j],
                                        Si['sigma'][j])
                          )
    elif method == 'sobol':
        title = 'Parameter'
        names = problem['names']
        D = problem['num_vars']
    
        with open('/tmp/results/%s' % filename, 'w') as f:
            f.write('%s S1 S1_conf ST ST_conf\n' % title)
            for j in range(D):
                f.write('%s %f %f %f %f\n' % (names[j], Si['S1'][
                    j], Si['S1_conf'][j], Si['ST'][j], Si['ST_conf'][j]))
        
            if calc_second_order:
                f.write('\n%s_1 %s_2 S2 S2_conf\n' % (title,title))
        
                for j in range(D):
                    for k in range(j + 1, D):
                        f.write("%s %s %f %f\n" % (names[j], names[k], 
                            Si['S2'][j, k], Si['S2_conf'][j, k]))