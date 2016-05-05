"""
idfsyntax.py
~~~~~~~~~~~~
Module to convert an idf based on the job parameters passed in. This can be
changed to suit the job in hand.

"""
import logging

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)


def set_lights(idf, job):
    lights = idf.idfobjects['LIGHTS']
    for light in lights:
        if light.Zone_or_ZoneList_Name.lower() == 'admin':
            light.Watts_per_Zone_Floor_Area = job['admin_light_wpm2']
        elif light.Zone_or_ZoneList_Name.lower() == 'class':
            light.Watts_per_Zone_Floor_Area = job['class_light_wpm2']


def set_equipment(idf, job):
    equips = idf.idfobjects['ELECTRICEQUIPMENT']
    for equip in equips:
        if equip.Zone_or_ZoneList_Name.lower() == 'admin':
            equip.Watts_per_Zone_Floor_Area = job['admin_equip_wpm2']
        elif equip.Zone_or_ZoneList_Name.lower() == 'class':
            equip.Watts_per_Zone_Floor_Area = job['class_equip_wpm2']


def set_weather(idf, job):
    if job['weather_file'] < 0.5:
        idf.epw = './data/cntr_Islington_TRY.epw'
    else:
        idf.epw = './data/2050_Islington_a1b_90_percentile_TRY.epw'


def set_infiltration(idf, job):
    infils = idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE']
    for infil in infils:
        infil.Air_Changes_per_Hour = job['infiltration']


def prepare_idf(idf, job):
    logging.debug("Editing IDF")
    for key, value in job.items():
        logging.debug("{}: {}".format(key, value))
    # weather file
    set_weather(idf, job)
    # equipment
    set_equipment(idf, job)
    # lighting
    set_lights(idf, job)
    # infiltration and ventilation
    set_infiltration(idf, job)
    
    # fabric U values (add dummy constructions)
    # set wall U values
    # set wall thermal mass
    # set floor U values
    # set floor thermal mass
    # set roof U values
    # set roof thermal mass
    
    # windows
    # set window U values
    # set window SHGC
    
    # thermal mass
    
    # schedules
    
    
    # HVAC efficiency
    # HVAC setpoints
    
    return idf

def make_construction(idf, name, layers):
    """Add opaque and glazed constructions to the IDF.
    
    Parameters
    ----------
    idf : eppy.modeleditor.IDF
        The IDF to be edited.
    name : str
        Name of the construction.
    layers : list of dicts
        List of dicts with layer materials and thicknesses.
        
    """
    construction = idf.newidfobject(
        'CONSTRUCTION',
        Name=name,
        Outside_Layer=layers.pop(0)
        )
    for i, parse_opaque_layers in enumerate(layers):
        construction['Layer_{0}'.format(i+2)] = parse_opaque_layers
