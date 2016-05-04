"""
sampler.py
~~~~~~~~~~

Generate samples from an input file.

"""
from SALib.analyze import sobol
from SALib.sample import saltelli

import numpy as np


def evaluate_model(X):
    print zip(problem['names'], X)
    return X

problem = {
    'num_vars': 19,
    'names': ['roof_u_value', 'wall_u_value', 'floor_u_value',
              'window_u_value', 'window_shgc',
              'window2wall', 
              'thermal_mass', 
              'class_equip_wpm2', 'admin_equip_wpm2', 
              'class_light_wpm2', 'admin_light_wpm2', 
              'schedules', 
              'heating_setpoint', 
              'cooling_setpoint',
              'ventilation', 
              'infiltration',
              'boiler_efficiency', 
              'cooling_efficiency',
              'weather_file'
              ],
    'bounds': [[0.2, 1.5],  # roof_u_value
               [0.2, 1.5],  # wall_u_value
               [0.2, 1.5],  # floor_u_value
               [1.5, 4.0],  # window_u_value
               [0.2, 0.8],  # window_shgc
               [0.2, 0.6],  # wwr
               [0, 1],      # thermal_mass
               [3, 9],      # class_equip_wpm2
               [9, 18],     # admin_equip_wpm2
               [5, 12],     # class_light_wpm2
               [8, 15],     # admin_light_wpm2
               [-0.1, 0.1], # schedules
               [17, 25],    # heating_setpoint
               [17, 25],    # cooling_setpoint
               [0.1, 0.2],  # ventilation
               [0.2, 1],    # infiltration
               [0.7, 0.9],  # boiler_efficiency
               [1, 3.5],    # cooling_efficiency
               [0, 1],      # weather_file
               ],
}

def samples():
    """Sample parameter values and return a generator of jobs.
    """
    runs = saltelli.sample(problem, 1, calc_second_order=False)
    as_floats = (zip(problem['names'], (float(n) for n in run)) 
                 for run in runs)

    return as_floats

def main():
    Y = np.empty([samples.shape[0]])
    
    for i, X in enumerate(samples):
        Y[i] = evaluate_model(X)
        
        
    Si = sobol.analyze(problem, Y, print_to_console=False, calc_second_order=False)
    
    print "Total:", Si['ST'].round(2)
    print "1st-order:", Si['S1'].round(2)
