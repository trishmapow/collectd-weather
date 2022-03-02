# WHY DOES COLLECTD STILL USE PYTHON 2 BY DEFAULT???

import collectd
import serial
from serial.tools.list_ports import comports
import time
import math

dev = next(x for x in comports() if x.name.startswith('ttyUSB')).device
s = serial.Serial(dev, timeout=1)
V = collectd.Values(host='', plugin='weather')
dir_map = {528: 0, 945: 45, 45: 90, 80: 135, 125: 180, 351: 225, 799: 270, 682: 315}
DIR_TOL = 1.1 # +/- % for dir_map
INTERVAL = 5 # reading frequency


def init():
    collectd.info('weather plugin: initialized')
    
def shutdown():
    s.close()
    
def read():
    readings = []
    while True:
        next_line = s.readline().decode('utf-8').strip().split(',')
        if len(next_line) == 6:
            readings.append(dict(x.split(':') for x in next_line))
        if not s.in_waiting:
            break
    if len(readings) == 0:
        return
    last_time = int(time.time())
    avg_temp = sum(float(reading['tempC']) for reading in readings) / len(readings)
    avg_lux = sum(float(reading['lux']) for reading in readings) / len(readings)
#    avg_gas = sum(int(reading['raw_gas']) for reading in readings) / len(readings)
    avg_speed = sum(float(reading['km/h']) for reading in readings) / len(readings)
    gust = max(float(reading['km/h']) for reading in readings)
    rain = sum(float(reading['rain_um']) for reading in readings) * 3.0 / 1000
    
    sum_sin = sum_cos = 0.0
    for reading in readings:
        dir_raw = int(reading['dir_raw'])
        for k, v in dir_map.items():
            if dir_raw >= k / DIR_TOL and dir_raw <= k * DIR_TOL:
                rad = math.radians(v)
                sum_sin += math.sin(rad)
                sum_cos += math.cos(rad)
                break
    avg_dir = math.degrees(math.atan2(sum_sin / len(readings), sum_cos / len(readings)))
    if sum_cos < 0:
        avg_dir += 180
    elif sum_sin < 0 and sum_cos > 0:
        avg_dir += 360
    avg_dir = 0.0 if avg_dir == 360 else avg_dir
    
    V.dispatch(type='weather_temp', type_instance='value', values=[avg_temp], time=last_time)
    V.dispatch(type='weather_lux', type_instance='value', values=[avg_lux], time=last_time)
#    V.dispatch(type='weather_gas', type_instance='value', values=[avg_gas], time=last_time)
    V.dispatch(type='weather_speed', type_instance='speed', values=[avg_speed], time=last_time)
    V.dispatch(type='weather_gust', type_instance='gust', values=[gust], time=last_time)
    V.dispatch(type='weather_dir', type_instance='dir', values=[avg_dir], time=last_time)
    V.dispatch(type='weather_rain', type_instance='value', values=[rain], time=last_time)
#    collectd.info(str(last_time) + ' ' + str(avg_temp))
    
collectd.register_init(init)
collectd.register_shutdown(shutdown)
collectd.register_read(read)
