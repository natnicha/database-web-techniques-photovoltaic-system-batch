import psycopg2 as pg
import pandas.io.sql as psql
import pandas as pd
import sys
import numpy as np
from datetime import datetime
from openpyxl import load_workbook

def getInfoFromDB(product_id):    
    connection = pg.connect("host=localhost dbname=postgres user=postgres password=root")
    sql_stmt = """SELECT Timezone('Europe/Berlin',w.datetime) as datetime, p.inclination, p.orientation, p.area, p.geolocation[0] as latitude, p.geolocation[1] as longitude, pj.start_at, w.air_temperature, w.humidity, s.name as model_name, s.efficiency
    FROM products p
    LEFT JOIN projects pj ON p.project_id = pj.id
    LEFT JOIN weather w ON w.geolocation ~= p.geolocation 
    LEFT JOIN solar_panel_models s ON s.id = p.solar_panel_model_id
    WHERE p.id = """+product_id+"""
    AND (w.datetime BETWEEN (pj.start_at - INTERVAL '30 day') AND (pj.start_at + INTERVAL '1 hour'))
    ORDER BY w.datetime 
    """
    timezone = datetime.now().tzname()
    connection.cursor(f"SET TIME ZONE {timezone};")
    return psql.read_sql(sql_stmt, connection)

def convertDegToRad(degree):
    return (degree/360)*2*np.pi

def calExtraterrestrialRadiation():
    return

def exportToExcel(dataframe):
    with pd.ExcelWriter('report.xlsx', engine='xlsxwriter') as writer:
        header = pd.DataFrame({
            'Project start on': dataframe['start_at'].dt.tz_localize(None),
            'Latitude (°)': dataframe['latitude'][0],
            'Longitude (°)': dataframe['longitude'][0],
            'Tilt/Inclination of PV panels (°)': dataframe['inclination'][0],
            'Azimuth/Orientation of PV panels (°)': dataframe['orientation'][0],
            'Area (m^2)': dataframe['area'][0],
            'Panel model model': dataframe['model_name'][0],
            'Panel model efficiency (%)': dataframe['efficiency'][0],
            'Total generated energy (kWh)': np.round(sum(dataframe.fillna(0)['energy (Wh)'])/1000, 4)
        }, index=[0])
        header.T.to_excel(writer, sheet_name='site-info', header=False)
        writer.sheets['site-info'].set_column('A:A', 30)
        writer.sheets['site-info'].set_column('B:B', 27)

        # dataframe['datetime'] = dataframe['datetime'].dt.tz_localize(None)
        dataframe['global-radiation'] = dataframe['global-radiation'].round(2)
        dataframe['energy (Wh)'] = dataframe['energy (Wh)'].round(2)
        dataframe = dataframe.rename(columns={'air_temperature': 'air-temperature (°C)', 'global-radiation': 'global irradiance on the inclined plane (W/m2)'})
        dataframe.fillna(0).to_excel(writer, sheet_name='hourly-profiles', index=False, 
            columns=['datetime', 'air-temperature (°C)', 'global irradiance on the inclined plane (W/m2)', 'energy (Wh)'])
        writer.sheets['hourly-profiles'].set_column('A:F', 20)

    file_name = 'report.xlsx'
    wb = load_workbook(file_name)
    return wb

def __init__():
    product_id = sys.argv[1]
    parameters = getInfoFromDB(product_id)
    parameters['latitude-rad'] =  convertDegToRad(parameters['latitude'])
    parameters['longitude-rad'] =  convertDegToRad(parameters['longitude'])
    parameters['inclination-rad'] =  convertDegToRad(parameters['inclination'])
    parameters['orientation-rad'] =  convertDegToRad(parameters['orientation'])
    parameters['day-of-year'] = parameters['datetime'].dt.dayofyear #pd.Period(parameters['start_at'].dt.date, freq='D')
    # number_of_day_in_this_year = datetime.strptime("3112" + str(parameters['start_at'][0].year), "%d%m%Y").timetuple().tm_yday
    parameters['declination-angle'] = -23.44*np.cos(convertDegToRad((360/365))*((parameters['day-of-year']-1)+10))  # -23.44*cos((360/365)*(d-10))
    # parameters['day-angle'] = 2*np.pi*(parameters['day-of-year']-1)/365
    # parameters['declination-angle'] = (0.006918-0.399912*np.cos(parameters['day-angle'])+0.070257*np.sin(parameters['day-angle'])-0.006758*np.cos(2*parameters['day-angle']))+0.000907*np.sin(2**parameters['day-angle']-0.002697*np.cos(3*parameters['day-angle'])+0.00148*np.sin(3*parameters['day-angle']))

    # parameters['hour-angle'] = np.min([np.abs(np.arccos(-np.tan(parameters['latitude-rad'])*np.tan(convertDegToRad(parameters['declination-angle'])))), np.abs(np.arccos(-np.tan(convertDegToRad(parameters['latitude']-parameters['orientation']))*np.tan(convertDegToRad(parameters['declination-angle']))))])
    # parameters['sunrise'] = 12-(parameters['hour-angle']/15)
    # parameters['sunset'] = 12+(parameters['hour-angle']/15)

    # parameters['w1'] = parameters[['datetime','sunrise', 'sunset']].apply(lambda x: (15* (x['datetime'].hour - 12)) if ((x['datetime'].hour >= np.floor(x['sunrise'])) & (x['datetime'].hour <= np.floor(x['sunset']))) else np.nan, axis=1)
    # parameters['w2'] = parameters[['datetime','sunrise', 'sunset']].apply(lambda x: (15* (x['datetime'].hour+1 - 12)) if ((x['datetime'].hour >= np.floor(x['sunrise'])) & (x['datetime'].hour <= np.floor(x['sunset']))) else np.nan, axis=1)
    # parameters['day-angle'] = 2*np.pi*(parameters['day-of-year']-1)/365
    # parameters['eccentricity'] =1.00011+0.034221*np.cos(parameters['day-angle'])+0.00128*np.sin(parameters['day-angle'])+0.000719*np.sin(2*parameters['day-angle'])+0.000077*np.sin(2*parameters['day-angle'])
    # # parameters['hourly-radiation'] = 43200/np.pi*4.921*(1+0.033*(360*parameters['day-of-year']/365))*(np.cos(parameters['latitude-rad'])*np.cos(convertDegToRad(parameters['declination-angle']))*np.sin(parameters['w2'])-np.sin(parameters['w1'])*((np.pi*parameters['w2']-parameters['w1'])/180)*np.sin(parameters['latitude-rad'])*np.cos(parameters['declination-angle']))
    # parameters['hourly-extraterrestrial'] = 12*60/np.pi*0.082*(1+0.033*(np.cos(2*np.pi*parameters['day-of-year']/365)))*((parameters['w2']-parameters['w1'])*np.sin(parameters['latitude-rad'])*np.sin(convertDegToRad(parameters['declination-angle']))+np.cos(parameters['latitude-rad'])*np.cos(convertDegToRad(parameters['declination-angle']))*(np.sin(parameters['w2'])-np.sin(parameters['w1'])))




    # # Ibeta = Hourly global solar radiation on inclined surface
    # # Idb = Hourly diffuse solar radiation on inclined surface
    # # Ibb = Hourly direct beam solar radiation on inclined surface
    # # Ir = Hourly ground reflected radiation on inclined surface
    # # Ih = Hourly global solar radiation on horizontal surface
    # # Id = Hourly diffuse solar radiation on horizontal surface
    # # Mt = Hourly clearness index # default = 0.2
    # # inclination = β (beta) = Tilt angle
    # # orientation = γ (gamma) = Solar Azimuth Angle 
    # # IbN = Hourly direct normal beam radiation on horizontal surface
    # # ρ = surface albedo # default = 0.31

    # parameters['B'] = convertDegToRad((360*(parameters['day-of-year']-81))/365.0)
    # parameters['ST'] = parameters['datetime'].dt.hour+(9.87*np.sin(2*parameters['B'])-7.53*np.cos(parameters['B'])-1.5*np.cos(parameters['B']))/60
    # parameters['hour-angle'] = 15*(12-parameters['ST'])
    # parameters['θz'] = (np.arccos(np.sin(convertDegToRad(parameters['declination-angle']))*np.sin(parameters['latitude-rad'])+np.cos(convertDegToRad(parameters['declination-angle']))*np.cos(parameters['latitude-rad'])*np.cos(convertDegToRad(parameters['hour-angle'])))*np.pi/180)

    # Mt = 0.2
    # A = 1088
    # B = 0.205
    # C = 0.134
    # parameters['cosθz'] = np.cos(parameters['θz'])
    # parameters['IbN']  = A*np.exp(-B/parameters['cosθz'])
    # parameters['Id'] = 1.0086-0.178*Mt # Chandrasekaran and Kumar’s Model
    # parameters['Ih'] = parameters['IbN'] * parameters['cosθz'] + parameters['Id']

    # parameters['Idbeta'] = ((3+np.cos(2*convertDegToRad(parameters['inclination'])))/4)*parameters['Id']
    # # -----------------------------------
    # # cosθ = (sin ϕ cos β − cos ϕ sin β cos γ) sin δ + (cos ϕ cos β + sin ϕ sin β cos γ) cos δ cos ω + cos δ sin β sin γ sin ω
    # parameters['cosθ'] = (np.sin(parameters['latitude-rad'])*np.cos(parameters['inclination-rad'])
    #                       -np.cos(parameters['latitude-rad'])*np.sin(parameters['inclination-rad'])*np.cos(parameters['orientation-rad']))*np.sin(convertDegToRad(parameters['declination-angle'])) +(
                            
    #                       np.cos(parameters['latitude-rad'])*np.cos(parameters['inclination-rad'])
    #                       +np.sin(parameters['latitude-rad'])*np.sin(parameters['inclination-rad'])*np.cos(parameters['orientation-rad']))*np.cos(convertDegToRad(parameters['declination-angle']))*np.cos(convertDegToRad(parameters['hour-angle'])) +(
    #                           np.cos(convertDegToRad(parameters['declination-angle']))*np.sin(parameters['inclination-rad'])*np.sin(parameters['inclination-rad']*np.sin(convertDegToRad(parameters['hour-angle'])))
    #                       )
    # parameters['rb'] = parameters['cosθ']/parameters['cosθz']
    # parameters['Ib'] = parameters['IbN'] * parameters['cosθz']
    # parameters['Ibbeta'] = parameters['rb'] + parameters['Ib']
    # # -----------------------------------
    # albedo=0.31
    # parameters['Ir'] = parameters['Ih']*albedo*((1-np.cos(parameters['inclination-rad']))/2)


    # parameters['Ibeta'] = parameters['Idbeta'] + parameters['Ibbeta'] + parameters['Ir']
    # # -----------------------------------

    # loss=1 # no loss
    # parameters['Energy'] = parameters['area']*parameters['efficiency']/100*parameters['Ibeta']*loss



    parameters['hour-angle'] = (360*(parameters['day-of-year']-81))/365.0
    parameters['B'] = convertDegToRad(parameters['hour-angle'])
    parameters['ST1'] = parameters['datetime'].dt.hour+(9.87*np.sin(2*parameters['B'])-7.53*np.cos(parameters['B'])-1.5*np.cos(parameters['B']))/60 + 4/60*(0-parameters['latitude-rad'])
    parameters['ST2'] = parameters['datetime'].dt.hour+1+(9.87*np.sin(2*parameters['B'])-7.53*np.cos(parameters['B'])-1.5*np.cos(parameters['B']))/60 + 4/60*(0-parameters['latitude-rad'])
    # parameters['w1'] = 15*(parameters['ST1']-12)
    # parameters['w2'] = 15*(parameters['ST2']-12)
    parameters['sunrise'] = 12-(parameters['hour-angle']/15)
    parameters['sunset'] = 12+(parameters['hour-angle']/15)
    parameters['w1'] = parameters[['datetime', 'ST1', 'sunrise', 'sunset']].apply(lambda x: (15* (x['ST1'] - 12)) if ((x['datetime'].hour >= np.floor(x['sunrise'])) & (x['datetime'].hour <= np.ceil(x['sunset']))) else np.nan, axis=1)
    parameters['w2'] = parameters[['datetime', 'ST2', 'sunrise', 'sunset']].apply(lambda x: (15* (x['ST2'] - 12)) if ((x['datetime'].hour >= np.floor(x['sunrise'])) & (x['datetime'].hour <= np.ceil(x['sunset']))) else np.nan, axis=1)


    parameters['longitude-difference'] = np.arctan(np.sin(parameters['inclination-rad'])*np.sin(parameters['orientation-rad'])/(np.cos(parameters['inclination-rad'])*np.cos(parameters['latitude-rad'])-np.sin(parameters['inclination-rad'])*np.sin(parameters['latitude-rad'])*np.cos(parameters['orientation-rad'])))
    parameters['equivalent-latitude'] = np.arcsin(np.sin(parameters['inclination-rad'])*np.cos(parameters['orientation-rad'])*np.cos(parameters['latitude-rad'])+np.cos(parameters['inclination-rad'])*np.sin(parameters['latitude-rad']))

    parameters['E0'] = 1+0.0033*np.cos(2*np.pi*parameters['day-of-year']/365)
    parameters['hourly-extraterrestrial'] = 12/np.pi*1367/24*parameters['E0']*(np.sin(parameters['equivalent-latitude'])*np.cos(convertDegToRad(parameters['declination-angle']))*(np.sin(convertDegToRad(parameters['w2'])+parameters['longitude-difference'])-np.sin(convertDegToRad(parameters['w1'])+parameters['longitude-difference']))+(parameters['w2']-parameters['w1'])*np.pi/180*np.sin(parameters['equivalent-latitude'])*np.sin(convertDegToRad(parameters['declination-angle'])))
    # parameters['hourly-extraterrestrial-horizontal-surface'] = 1367*parameters['E0']*(np.sin(parameters['latitude-rad'])*np.cos(convertDegToRad(parameters['declination-angle']))*(np.sin(convertDegToRad(parameters['w2']))-np.sin(convertDegToRad(parameters['w1'])))+(parameters['w2']-parameters['w1'])*np.pi/180*np.sin(parameters['latitude-rad'])*np.sin(convertDegToRad(parameters['declination-angle'])))

    parameters['vapor-presssure'] = 0.611*np.exp(17.3*parameters['air_temperature']/(parameters['air_temperature']+237.3))*parameters['humidity']/100
    parameters['dew-pt'] = (np.log(parameters['vapor-presssure'])+0.4926)/(0.0708-0.00421*np.log((parameters['vapor-presssure'])))
    parameters['precipitable-water'] = 1.12*np.exp(0.0614*parameters['dew-pt'])
    parameters['tsa'] = np.exp((-0.124-0.0207*parameters['precipitable-water'])+(-0.0682-0.0248*parameters['precipitable-water'])*3.6) #Optical Air Mass = 3.6
    parameters['direct-radiation'] = parameters['hourly-extraterrestrial']*parameters['tsa']

    parameters['ta'] = np.exp((-0.0363-0.0084*parameters['precipitable-water'])+(-0.0572-0.0173*parameters['precipitable-water'])*3.6)
    parameters['diffuse-radiation'] = 0.5*parameters['hourly-extraterrestrial']*parameters['ta'] 

    parameters['global-radiation'] = parameters['direct-radiation']+parameters['diffuse-radiation']
    loss = 1.0
    parameters['energy (Wh)'] = parameters['area']*parameters['efficiency']/100*parameters['global-radiation']*loss
    return exportToExcel(parameters)


