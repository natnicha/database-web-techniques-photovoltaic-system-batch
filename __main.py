# from numpy import array
# from solarpy import solar_panel
# from datetime import datetime

# panel = solar_panel(2.1, 0.1926, id_name='NYC_xmas')  # area surface, efficiency and name
# panel.set_orientation(array([5.2600, 11.4000, 0]))  # upwards
# panel.set_position(50.79342658311509, 12.9209, 0)  # NYC latitude, longitude, altitude
# panel.set_datetime(datetime(2023, 5, 13, 12, 0))  # Christmas Day!
# panel.power()



from numpy import array
from solarpy import solar_panel
from datetime import datetime

panel = solar_panel(2.1, 0.2, id_name='NYC_xmas')  # surface, efficiency and name
panel.set_orientation(array([5.2600, 11.4000, -1]))  # upwards
panel.set_position(50.82, 12.92, 0)  # NYC latitude, longitude, altitude
panel.set_datetime(datetime(2019, 12, 25, 16, 15))  # Christmas Day!
panel.power()