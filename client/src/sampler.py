"""
sampler.py
~~~~~~~~~~

Generate samples from an input file.

"""
import logging
import os

from SALib.analyze import sobol
from SALib.analyze import morris as analyse_morris
from SALib.sample import saltelli
from SALib.sample import morris as sample_morris
from SALib.util import read_param_file
import numpy as np


def evaluate_model(X):
    print zip(problem['names'], X)
    return X

problem = read_param_file('/client/data/parameters.txt')

def samples(method='morris', N=1):
    """Sample parameter values and return a generator of jobs.
    """
    if method == 'morris':
        runs = sample_morris.sample(problem, N, 4, 2)
    if method == 'saltelli':
        runs = saltelli.sample(problem, N, calc_second_order=True)
    logging.info("Creating %i jobs" % len(runs))
    empty_results = np.nan * np.empty(len(runs))

    return problem['names'], runs, empty_results


def analyse(X, Y, filename=None, method='morris', groups=None, 
            calc_second_order=True):
    if method == 'morris':
        Si = analyse_morris.analyze(problem, X, Y)
    if method == 'sobol':
        Si = sobol.analyze(problem, Y, calc_second_order=calc_second_order)
    # write results
    if filename:
        write_results(filename, Si, problem, method=method, groups=groups, 
                      calc_second_order=calc_second_order)


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
            elif groups is not None:
                # if there are groups, then the elementary effects returned need to be
                # computed over the groups of variables, rather than the individual variables
                Si_grouped = dict((k, [None] * num_vars)
                        for k in ['mu_star', 'mu_star_conf'])
                Si_grouped['mu_star'] = compute_grouped_metric(Si['mu_star'], groups)
                Si_grouped['mu_star_conf'] = compute_grouped_metric(Si['mu_star_conf'],
                                                                     groups)
                Si_grouped['names'] = unique_group_names
                Si_grouped['sigma'] = compute_grouped_sigma(Si['sigma'], groups)
                Si_grouped['mu'] = compute_grouped_sigma(Si['mu'], groups)
         
                f.write("{0:<30} {1:>10} {2:>10} {3:>15} {4:>10}\n".format(
                                    "Parameter",
                                    "Mu_Star",
                                    "Mu",
                                    "Mu_Star_Conf",
                                    "Sigma")
                      )
                for j in list(range(number_of_groups)):
                    f.write("{0:30} {1:10.3f} {2:10.3f} {3:15.3f} {4:10.3f}\n".format(
                                        Si_grouped['names'][j],
                                        Si_grouped['mu_star'][j],
                                        Si_grouped['mu'][j],
                                        Si_grouped['mu_star_conf'][j],
                                        Si_grouped['sigma'][j])
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