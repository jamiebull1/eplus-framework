"""
idfsyntax.py
~~~~~~~~~~~~
Module to convert an idf based on the job parameters passed in. This can be
changed to suit the job in hand.

"""
import logging

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

def set_u_value(idf, name, target_u):
    material = idf.getobject('MATERIAL', name)
    m = material.Thickness
    surface_R = 0.18
    material.Conductivity = m  / ((1 / target_u) - surface_R)
    
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
    set_ventilation(idf, job)
    
    # fabric U values (add dummy constructions)
    set_u_value(idf, 'wall', job['wall_u_value'])
    set_u_value(idf, 'floor', job['floor_u_value'])
    set_u_value(idf, 'roof', job['roof_u_value'])
    # set wall thermal mass
    # set floor thermal mass
    # set roof thermal mass
    
    # windows
    # set window U values
    # set window SHGC
    
    # thermal mass
    
    # schedules
    
    # HVAC
    set_hvac(idf, job)

    return idf


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
    for zone in idf.idfobjects['ZONE']:
        obj_name = '{} infiltration'.format(zone.Name)
        obj = idf.newidfobject('ZONEINFILTRATION:DESIGNFLOWRATE', obj_name)
        obj.Zone_or_ZoneList_Name = zone.Name
        obj.Design_Flow_Rate_Calculation_Method = "AirChanges/Hour"
        obj.Air_Changes_per_Hour = job['infiltration']
        obj.Schedule_Name = "AlwaysOn"
        
def set_ventilation(idf, job):
    for zone in idf.idfobjects['ZONE']:
        obj_name = '{} ventilation'.format(zone.Name)
        obj = idf.newidfobject('ZONEVENTILATION:DESIGNFLOWRATE', obj_name)
        obj.Zone_or_ZoneList_Name = zone.Name
        obj.Design_Flow_Rate_Calculation_Method = "Flow/Person"
        obj.Flow_Rate_per_Person = job['ventilation'] / 1000 # l/s to m3/s
        obj.Schedule_Name = "AlwaysOn"
        
def set_hvac(idf, job):
    kwargs = {'HVACTEMPLATE:PLANT:BOILER': 
              {'Efficiency': job['boiler_efficiency'],
               'Fuel_Type': 'NaturalGas'}}
    for zone in idf.idfobjects['ZONE']:
        boiler_only(idf, zone.Name, **kwargs)
    heating_stat = idf.getobject('SCHEDULE:COMPACT', 'HeatingSetpointSchedule')
    cooling_stat = idf.getobject('SCHEDULE:COMPACT', 'CoolingSetpointSchedule')
    heating_stat.Field_4 = job['heating_setpoint']
    cooling_stat.Field_4 = job['cooling_setpoint']
    

def boiler_only(idf, zone_name, **kwargs):
    """
    Add a boiler to the given IDF.
    
    Parameters
    ----------
    idf : eppy.modeleditor.IDF3
        The IDF to be edited.
    zone_name : str (or int?)
        The zone number of the zone for which the system is being added.
    storey : int
        The storey number used to set schedules.
        
    """
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:PLANT:BOILER',
        Name='Main Boiler',
        Boiler_Type='HotWaterBoiler',
        Priority=1,
        **kwargs['HVACTEMPLATE:PLANT:BOILER']
        )
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:THERMOSTAT',
        Name='Thermostat',
        Heating_Setpoint_Schedule_Name='HeatingSetpointSchedule',
        Cooling_Setpoint_Schedule_Name='CoolingSetpointSchedule',
        )
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:PLANT:HOTWATERLOOP',
        Name='Hot Water Loop',
        Hot_Water_Setpoint_Reset_Type='OutdoorAirTemperatureReset',
        )
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:ZONE:BASEBOARDHEAT',
        Zone_Name=zone_name,
        Baseboard_Heating_Type='HotWater',
        Template_Thermostat_Name='Thermostat',
        )

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

 
def add_or_replace_idfobject(idf, key, aname='', **kwargs):
    """
    This is used when there may be an object with the same signature in the
    IDF, for example we only want a single instance of a particular HVAC
    template. The approach taken is to remove and replace the object since we
    may want to change its characteristics.
    
    Parameters
    ----------
    idf : eppy.modeleditor.IDF3
        The IDF to be edited.
    key : str
        The EnergyPlus object type.
    aname : str
        Optionally the name of the object if it is not passed as one of the
        keyword aguments.

    """    
    try:
        name = kwargs['Name']
    except KeyError:
        name = aname
    if idf.getobject(key, name):
        idf.removeidfobject(idf.getobject(key, name))
    return idf.newidfobject(key, aname, **kwargs)



