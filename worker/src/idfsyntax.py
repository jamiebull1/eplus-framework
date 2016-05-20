"""
idfsyntax.py
~~~~~~~~~~~~
Module to convert an idf based on the job parameters passed in. This can be
changed to suit the job in hand.

"""
import logging

from eppy.modeleditor import IDF
from eppy.function_helpers import getcoords

#logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)


def prepare_idf(idf, job):
    logging.debug("Editing IDF")
#    for key, value in job.items():
#        logging.debug("{}: {}".format(key, value))
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
    set_windows(idf, job)
    # occupancy    
    set_occupancy(idf, job)
    # schedules
    
    # HVAC
    set_hvac(idf, job)
    # convection algorithms
    set_convection_algorithms(idf, job)
    # timesteps
    set_timestep(idf, job)
    # daylighting
    set_daylighting(idf, job)

    return idf


def set_windows(idf, job):
    wwr, u_value, shgc = (job['window2wall'], 
                          job['window_u_value'], 
                          job['window_shgc'])
    # set window properties
    layer = idf.newidfobject(
        'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', 
        Name = 'WindowGlazing',
        UFactor = u_value,
        Solar_Heat_Gain_Coefficient = shgc,        
        )
    construction = idf.newidfobject(
        'CONSTRUCTION',
        Name='dummy_window',
        Outside_Layer=layer.Name
        )
    
    # get external walls
    walls = [w for w in idf.idfobjects['BUILDINGSURFACE:DETAILED']
             if w.Outside_Boundary_Condition.lower() == 'outdoors'
             and w.Surface_Type.lower() == 'wall']
    # add windows
    for wall in walls:
        pts = window_vertices_given_wall_vertices(vertices(wall), wwr)
        window = idf.newidfobject('FENESTRATIONSURFACE:DETAILED',
            Name = wall.Name + " WINDOW",
            Surface_Type = 'Window',
            Construction_Name = 'dummy_window',
            Building_Surface_Name = wall.Name,
            Number_of_Vertices = len(pts)
        )
        for i, v in enumerate(pts):
            window['Vertex_{0}_Xcoordinate'.format(i+1)] = v[0]
            window['Vertex_{0}_Ycoordinate'.format(i+1)] = v[1]
            window['Vertex_{0}_Zcoordinate'.format(i+1)] = v[2]
        

def set_convection_algorithms(idf, job):
    interior = ['Simple', 'TARP', 'AdapativeConvectionAlgorithm']
    interior_algo = interior[int(round(job['interior_surface_convection']))]
    inside = idf.idfobjects['SURFACECONVECTIONALGORITHM:INSIDE'][0]
    inside.Algorithm = interior_algo
    exterior = ['SimpleCombined', 'DOE-2', 'TARP', 'AdapativeConvectionAlgorithm']
    exterior_algo = exterior[int(round(job['exterior_surface_convection']))]
    outside = idf.idfobjects['SURFACECONVECTIONALGORITHM:OUTSIDE'][0]
    outside.Algorithm = exterior_algo


def set_timestep(idf, job):
    steps = [4, 6, 12]
    timestep = idf.idfobjects['TIMESTEP'][0]
    timestep.Number_of_Timesteps_per_Hour = steps[int(round(job['timesteps_per_hour']))]


def set_daylighting(idf, job):
    if job['daylighting'] < 0.5:
        return
    for zone in idf.idfobjects['ZONE']:
        floor = [f for f in idf.idfobjects['BUILDINGSURFACE:DETAILED'] if f.Surface_Type.lower() == 'floor' and f.Zone_Name == zone.Name][0]
        coords = getcoords(floor)
        xs = [v[0] for v in coords]
        ys = [v[1] for v in coords]
        z = [v[2] for v in coords][0]
        x = sum(xs) / len(xs)
        y = sum(ys) / len(ys)
        daylight = idf.newidfobject(
            'DAYLIGHTING:CONTROLS', 
            Zone_Name = zone.Name, 
            Total_Daylighting_Reference_Points = 1, 
            XCoordinate_of_First_Reference_Point = x, 
            YCoordinate_of_First_Reference_Point = y, 
            ZCoordinate_of_First_Reference_Point = z + 0.8, 
            Glare_Calculation_Azimuth_Angle_of_View_Direction_Clockwise_from_Zone_yAxis=90,
            Lighting_Control_Type = 2,
            Number_of_Stepped_Control_Steps = 1,
            )


def set_occupancy(idf, job):
    occupants = idf.idfobjects['PEOPLE']
    for occ in occupants:
        if occ.Zone_or_ZoneList_Name.lower() == 'admin':
            occ.People_per_Zone_Floor_Area = job['admin_occupancy']
        elif occ.Zone_or_ZoneList_Name.lower() == 'class':
            occ.People_per_Zone_Floor_Area = job['class_occupancy']


def set_u_value(idf, name, target_u):
    material = idf.getobject('MATERIAL', name)
    m = material.Thickness
    surface_R = 0.18
    material.Conductivity = m  / ((1 / target_u) - surface_R)
 
    
def set_thermal_mass(idf, name, target_u):
    material = idf.getobject('MATERIAL', name)
    m = material.Thickness
    surface_R = 0.18
    material.Conductivity = m  / ((1 / target_u) - surface_R)
    

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
        obj = idf.newidfobject(
            'ZONEINFILTRATION:DESIGNFLOWRATE',
            Name = obj_name,
            Zone_or_ZoneList_Name = zone.Name,
            Design_Flow_Rate_Calculation_Method = "AirChanges/Hour",
            Air_Changes_per_Hour = job['infiltration'],
            Schedule_Name = "AlwaysOn")
        
def set_ventilation(idf, job):
    for zone in idf.idfobjects['ZONE']:
        obj_name = '{} ventilation'.format(zone.Name)
        obj = idf.newidfobject(
            'ZONEVENTILATION:DESIGNFLOWRATE',
            Name = obj_name,
            Zone_or_ZoneList_Name = zone.Name,
            Design_Flow_Rate_Calculation_Method = "Flow/Person",
            Flow_Rate_per_Person = job['ventilation'] / 1000, # l/s to m3/s
            Schedule_Name = "AlwaysOn")
        
def set_hvac(idf, job):
    kwargs = {'HVACTEMPLATE:PLANT:BOILER': 
              {'Efficiency': job['boiler_efficiency'],
               'Fuel_Type': 'NaturalGas'}}
    for zone in idf.idfobjects['ZONE']:
        if job['detailed_hvac'] < 0.5:
            ideal_loads(idf, zone.Name, **kwargs)
        else:
            boiler_only(idf, zone.Name, **kwargs)
    heating_stat = idf.getobject('SCHEDULE:COMPACT', 'HeatingSetpointSchedule')
    cooling_stat = idf.getobject('SCHEDULE:COMPACT', 'CoolingSetpointSchedule')
    heating_stat.Field_4 = job['heating_setpoint']
    cooling_stat.Field_4 = job['cooling_setpoint']
    

def ideal_loads(idf, zone_name, **kwargs):
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:THERMOSTAT',
        Name='Thermostat',
        Heating_Setpoint_Schedule_Name='HeatingSetpointSchedule',
        Cooling_Setpoint_Schedule_Name='CoolingSetpointSchedule',
        )
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM', '',
        Zone_Name=zone_name,
    Template_Thermostat_Name='Thermostat',
        )

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

def window_vertices_given_wall_vertices(vertices, glazing_ratio):
    """
    Calculate window vertices given wall vertices and glazing ratio.
    For each axis:
    1) Translate the axis points so that they are centred around zero
    2) Either:
        a) Multiply the z dimension by the glazing ratio to shrink it vertically
        b) Multiply the x or y dimension by 0.995 to keep inside the surface
    3) Translate the axis points back to their original positions
    
    Parameters
    ----------
    vertices : list of lists
        List of [x, y, z] vertices, starting a the top left of a surface and
        working around it counterclockwise. We expect each surface to have four
        vertices.
    
    Returns
    -------
    list 
        Window vertices bounding a vertical strip midway up the surface.
    
    """
    average_x = sum([x for x, _y, _z in vertices]) / len(vertices)
    average_y = sum([y for _x, y, _z in vertices]) / len(vertices)
    average_z = sum([z for _x, _y, z in vertices]) / len(vertices)
    # move windows in 0.5% from the edges so they can be drawn in SketchUp
    window_points = [[
                      ((x - average_x) * 0.995) + average_x,
                      ((y - average_y) * 0.995) + average_y,
                      ((z - average_z) * glazing_ratio) + average_z
                      ]
                     for x, y, z in vertices]

    return window_points

def vertices(surface):
    """Get vertices as (x,y,z) tuples.
    """
    return getcoords(surface)
    