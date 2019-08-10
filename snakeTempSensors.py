# This Python file uses the following encoding: utf-8
##############################################################################
#                  __     ______               ____
#   ___ ___  ___ _/ /____/_  __/__ __ _  ___  / __/__ ___  ___ ___  _______
#  (_-</ _ \/ _ `/  '_/ -_) / / -_)  ' \/ _ \_\ \/ -_) _ \(_-</ _ \/ __(_-<
# /___/_//_/\_,_/_/\_\\__/_/  \__/_/_/_/ .__/___/\__/_//_/___/\___/_/ /___/
#                                     /_/
#
##############################################################################
# Title:        snakeTempSensors
# Version:      1.0
# Description:  Provides temperature control for snake encloure
# Author:       Jonas Werner
##############################################################################
import os
import glob
import time
import json
from influxdb import InfluxDBClient
from datetime import datetime
import RPi.GPIO as GPIO


base_dir = '/sys/bus/w1/devices/'
locations = ["hotZoneMat", "coldZoneWaterbowl", "hotZoneSkull", "hotZoneHide", "coldZoneHide"]
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(5,GPIO.OUT)
GPIO.setup(6,GPIO.OUT)

# Set lamp off and mat on by default
GPIO.output(5,GPIO.HIGH)
GPIO.output(6,GPIO.HIGH)

# Set environment variables
host            = os.environ['influxDBHost']
port            = os.environ['influxDBPort']
user            = os.environ['influxDBUser']
password        = os.environ['influxDBPass']
dbname          = os.environ['influxDBName']

redisHost  = os.environ['redisHost']
redisPort  = os.environ['redisPort']
redisPass  = os.environ['redisPass']


def influxDBconnect():
    influxDBConnection = InfluxDBClient(host, port, user, password, dbname)
    return influxDBConnection


def redisDBconnect():
    redisDBConnection = redis.Redis(host=redisHost, port=redisPort, password=redisPass)
    return redisDBConnection


def influxDBwrite(device, sensorName, sensorValue):

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    measurementData = [
        {
            "measurement": device,
            "tags": {
                "gateway": device,
                "location": "Tokyo"
            },
            "time": timestamp,
            "fields": {
                sensorName: sensorValue
            }
        }
    ]
    influxDBConnection.write_points(measurementData, time_precision='ms')



def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def heatControl(appliance, desiredState):
    # The heat mat and heat lamp have different default states.
    # As the lamp is off by default it needs to be turned on with GPIO.LOW
    if appliance == "heatMat":
        if desiredState == "on":
            GPIO.output(6,GPIO.HIGH)
            redisDBConnection.hmset("snakeHeatmatStatus", {'power':1})
        elif desiredState == "off":
            GPIO.output(6,GPIO.LOW)
            redisDBConnection.hmset("snakeHeatmatStatus", {'power':0})

    elif appliance == "heatLamp":
        if desiredState == "on":
            GPIO.output(5,GPIO.LOW)
            redisDBConnection.hmset("snakeHeatLampStatus", {'power':1})
        elif desiredState == "off":
            GPIO.output(5,GPIO.HIGH)
            redisDBConnection.hmset("snakeHeatLampStatus", {'power':0})


influxDBConnection = influxDBconnect()
redisDBConnection = redisDBconnect()

while True:

    for i in range(0,5):
        device_folder = glob.glob(base_dir + '28*')[i]
        device_file = device_folder + '/w1_slave'

        temp = read_temp()
        print("Temperature at: %s: %s" % (locations[i], temp))
        if int(temp) < 80:
            influxDBwrite(locations[i], "Temperature", temp)

        # HotZone: Heat mat
        if i == 0:
            if int(temp) > 41:
                heatControl("heatMat", "off")
            elif int(temp) < 39:
                heatControl("heatMat", "on")

        # ColdZone: Waterbowl
        if i == 1:
            if int(temp) > 26:
                heatControl("heatLamp", "off")
            elif int(temp) < 25:
                heatControl("heatLamp", "on")

        time.sleep(5)
