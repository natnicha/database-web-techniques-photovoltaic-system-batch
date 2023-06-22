import os
import psycopg2 as pg
import pandas.io.sql as psql
import pandas as pd
import sys
import numpy as np
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from dotenv import load_dotenv

def getInfoFromDB(product_id):
    load_dotenv()

    url = URL.create(
        drivername=os.getenv("DB_DRIVER"),
        host=os.getenv("DB_HOST"),
        username=os.getenv("DB_USER"),
        database=os.getenv("DB_NAME"),
        password=os.getenv("DB_PASSWORD")
    )   
    engine = create_engine(url)
    connection = engine.connect()
    sql_stmt = """SELECT Timezone('Europe/Berlin',w.datetime) as datetime, p.inclination, p.orientation, p.area, p.geolocation[0] as latitude, p.geolocation[1] as longitude, pj.start_at, w.air_temperature, w.humidity, s.name as model_name, s.efficiency, pj.user_id
    FROM products p
    LEFT JOIN projects pj ON p.project_id = pj.id
    LEFT JOIN weather w ON w.geolocation ~= p.geolocation 
    LEFT JOIN solar_panel_models s ON s.id = p.solar_panel_model_id
    WHERE p.id = """+product_id+"""
    AND (w.datetime BETWEEN (pj.start_at - INTERVAL '30 day') AND (pj.start_at + INTERVAL '1 hour'))
    ORDER BY w.datetime 
    """
    return psql.read_sql(sql_stmt, connection)

def convertDegToRad(degree):
    return (degree/360)*2*np.pi

def calExtraterrestrialRadiation():
    return

def exportToExcel(dataframe):
    userId = str(dataframe['user_id'][0])
    uniqueName = str(dataframe['latitude'][0]) +'&'+ str(dataframe['longitude'][0])
    with pd.ExcelWriter(f'{userId}-PV-report-{uniqueName}.xlsx', engine='xlsxwriter') as writer:
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

        dataframe['global-radiation'] = dataframe['global-radiation'].round(2)
        dataframe['energy (Wh)'] = dataframe['energy (Wh)'].round(2)
        dataframe = dataframe.rename(columns={'air_temperature': 'air-temperature (°C)', 'global-radiation': 'global irradiance on the inclined plane (W/m2)'})
        dataframe.fillna(0).to_excel(writer, sheet_name='hourly-profiles', index=False, 
            columns=['datetime', 'air-temperature (°C)', 'global irradiance on the inclined plane (W/m2)', 'energy (Wh)'])
        writer.sheets['hourly-profiles'].set_column('A:F', 20)
    return

if __name__ == '__main__':
    product_id = sys.argv[1]
    parameters = getInfoFromDB(product_id)
    parameters['latitude-rad'] =  convertDegToRad(parameters['latitude'])
    parameters['longitude-rad'] =  convertDegToRad(parameters['longitude'])
    parameters['inclination-rad'] =  convertDegToRad(parameters['inclination'])
    parameters['orientation-rad'] =  convertDegToRad(parameters['orientation'])
    parameters['day-of-year'] = parameters['datetime'].dt.dayofyear
    parameters['declination-angle'] = -23.44*np.cos(convertDegToRad((360/365))*((parameters['day-of-year']-1)+10))  # -23.44*cos((360/365)*(d-10))

    parameters['hour-angle'] = (360*(parameters['day-of-year']-81))/365.0
    parameters['B'] = convertDegToRad(parameters['hour-angle'])
    parameters['ST1'] = parameters['datetime'].dt.hour+(9.87*np.sin(2*parameters['B'])-7.53*np.cos(parameters['B'])-1.5*np.cos(parameters['B']))/60 + 4/60*(0-parameters['latitude-rad'])
    parameters['ST2'] = parameters['datetime'].dt.hour+1+(9.87*np.sin(2*parameters['B'])-7.53*np.cos(parameters['B'])-1.5*np.cos(parameters['B']))/60 + 4/60*(0-parameters['latitude-rad'])
    parameters['sunrise'] = 12-(parameters['hour-angle']/15)
    parameters['sunset'] = 12+(parameters['hour-angle']/15)
    parameters['w1'] = parameters[['datetime', 'ST1', 'sunrise', 'sunset']].apply(lambda x: (15* (x['ST1'] - 12)) if ((x['datetime'].hour >= np.floor(x['sunrise'])) & (x['datetime'].hour <= np.ceil(x['sunset']))) else np.nan, axis=1)
    parameters['w2'] = parameters[['datetime', 'ST2', 'sunrise', 'sunset']].apply(lambda x: (15* (x['ST2'] - 12)) if ((x['datetime'].hour >= np.floor(x['sunrise'])) & (x['datetime'].hour <= np.ceil(x['sunset']))) else np.nan, axis=1)


    parameters['longitude-difference'] = np.arctan(np.sin(parameters['inclination-rad'])*np.sin(parameters['orientation-rad'])/(np.cos(parameters['inclination-rad'])*np.cos(parameters['latitude-rad'])-np.sin(parameters['inclination-rad'])*np.sin(parameters['latitude-rad'])*np.cos(parameters['orientation-rad'])))
    parameters['equivalent-latitude'] = np.arcsin(np.sin(parameters['inclination-rad'])*np.cos(parameters['orientation-rad'])*np.cos(parameters['latitude-rad'])+np.cos(parameters['inclination-rad'])*np.sin(parameters['latitude-rad']))

    parameters['E0'] = 1+0.0033*np.cos(2*np.pi*parameters['day-of-year']/365)
    parameters['hourly-extraterrestrial'] = 12/np.pi*1367/24*parameters['E0']*(np.sin(parameters['equivalent-latitude'])*np.cos(convertDegToRad(parameters['declination-angle']))*(np.sin(convertDegToRad(parameters['w2'])+parameters['longitude-difference'])-np.sin(convertDegToRad(parameters['w1'])+parameters['longitude-difference']))+(parameters['w2']-parameters['w1'])*np.pi/180*np.sin(parameters['equivalent-latitude'])*np.sin(convertDegToRad(parameters['declination-angle'])))

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
    exportToExcel(parameters)
    sys.exit(0)
