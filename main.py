import psycopg2 as pg
import pandas.io.sql as psql
import sys


product_id = sys.argv[1]
connection = pg.connect("host=localhost dbname=postgres user=postgres password=root")
sql_stmt = """SELECT p.inclination, p.orientation, p.area, p.geolocation, pj.start_at, w.datetime, w.air_temperature, w.humidity, s.efficiency
FROM products p
LEFT JOIN projects pj ON p.project_id = pj.id
LEFT JOIN weather w ON w.geolocation ~= p.geolocation 
LEFT JOIN solar_panel_models s ON s.id = p.solar_panel_model_id
WHERE p.id = """+product_id+"""
AND (w.datetime BETWEEN (pj.start_at - INTERVAL '30 day') AND pj.start_at)
"""
parameters = psql.read_sql(sql_stmt, connection)
print(parameters)

output_path = "."
parameters.to_csv(output_path)
