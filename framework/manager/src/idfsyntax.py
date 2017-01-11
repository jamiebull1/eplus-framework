"""
idfsyntax.py
~~~~~~~~~~~~
Module to convert an idf based on the job parameters passed in. This can be
changed to suit the job in hand.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os

from eppy.function_helpers import getcoords
from eppy.iddcurrent import iddcurrent
from geomeppy import IDF
from geomeppy.polygons import Polygon
from geomeppy.vectors import Vector3D  # used inside eval
from six import StringIO

from src.schedules import activities_proportions
from src.schedules import make_rates
from src.schedules import make_schedules
from src.schedules import stretch


#from worker.tests.test_schedules import activities_proportions
THIS_DIR = os.path.abspath(os.path.dirname(__file__))

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(filename='../var/log/eplus.log', level=logging.DEBUG)

DDY = './data/weather/islington/cntr_Islington_TRY.ddy'

def init_idf():
    """Initialise an IDF.
    """
    iddfhandle = StringIO(iddcurrent.iddtxt)
    if IDF.getiddname() == None:
        IDF.setiddname(iddfhandle)
    idf = IDF()
    return idf


def prepare_idf(idf, job, school):
    logging.debug("Editing IDF")
    for key, value in job.items():
        logging.debug("{}: {}".format(key, value))
    # geometry
    idf = set_geometry(idf, job, school)
    # weather file
    set_weather(idf, job)
    # equipment
    set_equipment(idf, job)
    # occupancy
    set_occupancy(idf, job)
    # schedules
    set_schedules(idf, job)
    # lighting
    set_lights(idf, job)
    # HVAC
    set_hvac(idf, job)
    # infiltration and ventilation
    set_infiltration(idf, job)
    set_ventilation(idf, job)
    # windows
    set_windows(idf, job)
    # convection algorithms
    set_convection_algorithms(idf, job)
    # timesteps
    set_timestep(idf, job)
    # daylighting
    set_daylighting(idf, job)

    # fabric U values (add dummy constructions)
    set_u_value(idf, 'ExternalWallMaterialInner', job['wall_u_value'])
    set_u_value(idf, 'ExternalFloorMaterialInner', job['floor_u_value'])
    set_u_value(idf, 'ExternalRoofMaterialInner', job['roof_u_value'])

    set_density(idf, 'ExternalWallMaterialInner', job['density'])
    set_density(idf, 'ExternalFloorMaterialInner', job['density'])
    set_density(idf, 'ExternalRoofMaterialInner', job['density'])

    return idf
    # set wall thermal mass
    # set floor thermal mass
    # set roof thermal mass


def set_geometry(idf, job, school):
    """Build the geometry for the IDF.
    """
    name = school[0]
    blocks = school[1]['blocks']
    shading_blocks = school[1]['shading_blocks']
    
    idf = build_school(idf, name, blocks, shading_blocks)
    return idf


def build_school(idf, schoolname, blocks, shading_blocks):
    """Build a school.
    
    Parameters
    ----------
    schoolname : str
        Name of the school.
    blocks : 
    """
    for block in blocks:
        name = block['name']
        poly = Polygon(eval(block['wkt']))        
        height = float(block['height'])
        if not height:
            height = 3.25
        num_storeys = int(block['num_storeys'])
        idf.add_block(name, poly.vertices, height, num_storeys)
    for block in shading_blocks:
        name = block['name']
        poly = Polygon(eval(block['wkt']))        
        height = float(block['height'])
        if not height:
            continue
        num_storeys = 1
        idf.add_shading_block(name, poly.vertices, height)
    
    logging.debug('intersecting')
    idf.intersect()
    logging.debug('matching')
    idf.match()
#    logging.debug('setting wwr')
#    idf.set_wwr(0.3)
    logging.debug('setting constructions')
    for surface in idf.getsurfaces():
        set_construction(surface)
    for surface in idf.idfobjects['FENESTRATIONSURFACE:DETAILED']:
        set_construction(surface)
    logging.debug('translating')
    idf.translate_to_origin()

    return idf


def set_construction(surface):
    if surface.Surface_Type.lower() == 'wall':
        if surface.Outside_Boundary_Condition.lower() == 'outdoors':
            surface.Construction_Name = 'Project Wall'
        elif surface.Outside_Boundary_Condition.lower() == 'ground':
            surface.Construction_Name = 'Project Wall'
        else:
            surface.Construction_Name = 'Project Partition'
    if surface.Surface_Type.lower() == 'floor':
        if surface.Outside_Boundary_Condition.lower() == 'ground':
            surface.Construction_Name = 'Project Ground Floor'
        else:
            surface.Construction_Name = 'Project Ground Floor'
    if surface.Surface_Type.lower() == 'roof':
        surface.Construction_Name = 'Project Flat Roof'
    if surface.Surface_Type.lower() == 'ceiling':
        surface.Construction_Name = 'Project Ceiling'
    if surface.Surface_Type.lower() == 'window':
        surface.Construction_Name = 'Project External Window'


def set_weather(idf, job):
    """Set the weather file for the job.
    
    Parameters
    ----------
    idf : IDF
        An Eppy IDF object.
    job : dict
        Dict containing the parameters.

    """
    if job['weather_file'] < 0.5:
        idf.epw = './data/weather/islington/cntr_Islington_TRY.epw'
    else:
        idf.epw = './data/weather/islington/2050_Islington_a1b_90_percentile_TRY.epw'


def set_occupancy(idf, job):
    """Set up occupancy for each zone.
    
    Parameters
    ----------
    idf : IDF
        An Eppy IDF object.
    job : dict
        Dict containing the parameters.

    """
    zones = idf.idfobjects['ZONE']
    for zone in zones:
        item = idf.newidfobject('PEOPLE')
        item.Name = '%s occupancy' % zone.Name
        item.Zone_or_ZoneList_Name = zone.Name
        item.Number_of_People_Calculation_Method='People/Area'
        item.People_per_Zone_Floor_Area = job['occupancy']
        item.Fraction_Radiant = '0.3'
        item.Number_of_People_Schedule_Name = '%s_Occ' % zone.Name
        item.Activity_Level_Schedule_Name = '%s_Metab' % zone.Name


def set_equipment(idf, job):
    """Set up equipment loads for each zone.
    
    Parameters
    ----------
    idf : IDF
        An Eppy IDF object.
    job : dict
        Dict containing the parameters.

    """
    zones = idf.idfobjects['ZONE']
    for zone in zones:
        item = idf.newidfobject('ELECTRICEQUIPMENT')
        item.Name = '%s equipment' % zone.Name
        item.Zone_or_ZoneList_Name = zone.Name
        item.Design_Level_Calculation_Method='Watts/Area'
        item.Schedule_Name = 'AlwaysOn'
        item.Watts_per_Zone_Floor_Area = job['equip_wpm2']


def set_schedules(idf, job):
    """Set up schedules for each zone.
    
    Required schedule types are occupancy, lighting, heating, cooling, 
    equipment, and metabolism.
    
    Parameters
    ----------
    idf : IDF
        An Eppy IDF object.
    job : dict
        Dict containing the parameters.

    """
    zones = idf.idfobjects['ZONE']

    gifa = sum(s.area for s in idf.getsurfaces('floor'))
    activities = activities_proportions(gifa)

    schedule_types = ['Heat', 'Cool', 'Light', 'Equip', 'Occ']
    schedules = make_schedules(zones, schedule_types, activities)
    coef = 1 + float(job['schedules'])
    for zone in schedules:
        for st in schedules[zone]:
            schedules[zone][st] = stretch(schedules[zone][st], coef, 12)

    write_schedules(idf, schedules, 'school')

    rate_types = ['Metab']
    rates = make_rates(zones, rate_types, activities)
    write_rates(idf, rates)


def write_schedules(idf, all_zone_schedules, record):
    """Add area weighted schedules for all activity zones to the IDF.
    
    Parameters
    ----------
    all_zone_schedules : dict
       Dictionary containing hourly schedules for each schedule type.
    record : int or str
        Name of the record.
    
    """
    col_num = 1
    for zone in all_zone_schedules:
#        logging.info(zone)
        for st in all_zone_schedules[zone]:
            idf.newidfobject(
                'SCHEDULE:FILE',
                Name='%s_%s' % (zone, st),
                Schedule_Type_Limits_Name='Any Number',
                File_Name='{}_schedules.csv'.format(record),
                Column_Number=col_num,
                Rows_to_Skip_at_Top=1,
                Number_of_Hours_of_Data=len(all_zone_schedules[zone][st]),
                Column_Separator='Comma'
                )
            col_num += 1
    write_schedules_file(all_zone_schedules, record)


def write_rates(idf, all_zone_rates):
    """
    Add area weighted schedules for all activity zones to the IDF. This is for
    things like metabolic rate which is a constant value modified by the
    occupancy schedule.
    
    Parameters
    ----------
    all_zone_rates : dict
       Dictionary containing peak rates for each rate schedule type.
    
    """
#    logging.info(all_zone_rates)
    for zone in all_zone_rates:
        for rate in all_zone_rates[zone]:
            idf.newidfobject(
                'SCHEDULE:COMPACT',
                Name='%s_%s' % (zone, rate),
                Schedule_Type_Limits_Name='Any Number',
                Field_1='Through: 12/31',
                Field_2='For: Alldays',
                Field_3='Until: 24:00,{0}'.format(all_zone_rates[zone][rate])
                )
        
        
def write_schedules_file(all_zone_schedules, record):
    """
    Write out the hourly schedules to a 'schedule.csv' file in the working
    directory.
    
    Parameters
    ----------
    all_zone_schedules : list
        A list of all the schedules for all the zones.
    record : int or str
        Name of the record.

    """
    csv_filename = '{}_schedules.csv'.format(record)
    hourly_schedules = []
    for zone in all_zone_schedules:
        for st in all_zone_schedules[zone]:
            hourly_schedules += [all_zone_schedules[zone][st]]
    # transpose to tuples for each hour
    hourly_schedules = zip(*hourly_schedules)
    header = []
    for zone in all_zone_schedules:
        for st in all_zone_schedules[zone]:
            header += ['%s_%s' % (zone, st)]
    header = ','.join(header) + '\n'
    with open(csv_filename, 'wb') as csv:
        csv.write(header)
        for hour in hourly_schedules:
            # Convert from numpy datatypes
            csv.write(','.join([str(h) for h in hour]) + '\n')


def set_windows(idf, job):
    wwr, u_value, shgc = (job['window2wall'], 
                          job['window_u_value'], 
                          job['window_shgc'])
    # set window properties
    layer = add_or_replace_idfobject(idf, 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM')
    layer.Name = 'ExternalWindowMaterial'
    layer.UFactor = u_value
    layer.Solar_Heat_Gain_Coefficient = shgc
    construction = add_or_replace_idfobject(idf, 'CONSTRUCTION')
    construction.Name = 'Project External Window'
    construction.Outside_Layer = layer.Name
    # set window:wall ratio
    idf.set_wwr(wwr)
    windows = idf.idfobjects['FENESTRATIONSURFACE:DETAILED']
    for window in windows:
        window.Construction_Name = 'Project External Window'
        

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


def set_u_value(idf, name, target_u):
    material = idf.getobject('MATERIAL', name)
    m = material.Thickness
    surface_R = 0.18
    material.Conductivity = m  / ((1 / target_u) - surface_R)
 
    
def set_density(idf, name, density):
    material = idf.getobject('MATERIAL', name)
    material.Density = density
    

def set_lights(idf, job):
    zones = idf.idfobjects['ZONE']
    for zone in zones:
        item = idf.newidfobject('LIGHTS')
        item.Name = '%s lights' % zone.Name
        item.Zone_or_ZoneList_Name = zone.Name
        item.Design_Level_Calculation_Method='Watts/Area'
        item.Schedule_Name = 'AlwaysOn'
        item.Watts_per_Zone_Floor_Area = job['light_wpm2']


def set_infiltration(idf, job):
    zones = idf.idfobjects['ZONE']
    for zone in zones:
        item = idf.newidfobject('ZONEINFILTRATION:DESIGNFLOWRATE')
        item.Name = '{} infiltration'.format(zone.Name)
        item.Zone_or_ZoneList_Name = zone.Name
        item.Design_Flow_Rate_Calculation_Method = "AirChanges/Hour"
        item.Air_Changes_per_Hour = job['infiltration']
        item.Schedule_Name = "AlwaysOn"
        
        
def set_ventilation(idf, job):
    zones = idf.idfobjects['ZONE']
    for zone in zones:
        item = idf.newidfobject('ZONEVENTILATION:DESIGNFLOWRATE')
        item.Name = '{} ventilation'.format(zone.Name)
        item.Zone_or_ZoneList_Name = zone.Name
        item.Design_Flow_Rate_Calculation_Method = "Flow/Person"
        item.Flow_Rate_per_Person = job['ventilation'] / 1000 # l/s to m3/s
        item.Schedule_Name = "AlwaysOn"
        

def set_natural_ventilation(idf, job):
    pass


def set_hvac(idf, job):
    kwargs = {'HVACTEMPLATE:PLANT:BOILER': 
              {'Efficiency': job['boiler_efficiency'],
               'Fuel_Type': 'NaturalGas'}}
    for zone in idf.idfobjects['ZONE']:
        if job['detailed_hvac'] < 0.5:
            ideal_loads(idf, zone.Name, **kwargs)
        else:
            boiler_only(idf, zone.Name, **kwargs)
    set_sizing_periods(idf, DDY)
    

def set_sizing_periods(idf, DDY):
    """Fetch SizingPeriod:DesignDay objects for the record.
    """
    idf2 = IDF(DDY)
    
    design_days = idf2.idfobjects['SIZINGPERIOD:DESIGNDAY']
    heating_ddy = [ddy for ddy in design_days if 'Htg 99%' in ddy.Name][0]
    idf.copyidfobject(heating_ddy)

    cooling_ddy = [ddy for ddy in design_days if 'Clg 1%' in ddy.Name][0]
    idf.copyidfobject(cooling_ddy)

    
def ideal_loads(idf, zone_name, **kwargs):
    add_or_replace_idfobject(idf,
        'HVACTEMPLATE:THERMOSTAT',
        Name='Thermostat',
        Heating_Setpoint_Schedule_Name='%s_Heat' % zone_name,
        Cooling_Setpoint_Schedule_Name='%s_Cool' % zone_name,
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
        Heating_Setpoint_Schedule_Name='%s_Heat' % zone_name,
        Cooling_Setpoint_Schedule_Name='%s_Cool' % zone_name,
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
    