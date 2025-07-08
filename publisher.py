#!/usr/bin/env python3

import urllib.request
import json
from pprint import pprint
from vevor import Vevor
from coil import Coil, CoilChargeState

import paho.mqtt.client as mqtt

from dataclasses import dataclass
from time import sleep

vevor_modes = [ "Power ON", "Standby", "Grid", "Off-Grid", "Bypass", "Charging", "Fault" ]

@dataclass
class mqtt_conf:
    host: str = "homeassistant.iot.wielun.int.kitor.pl"
    port: int = 1883
    user: str = "mqtt_wmbusmeters"
    pwd: str  = "nji9)OKM"

class MqttClient:
    def __init__(self, uri, port, user, pw):
        self.client = mqtt.Client(
            client_id = "wmbusmeters_py",
            transport = "tcp",
            protocol  = mqtt.MQTTv311,
            clean_session = True)

        self.client.username_pw_set(user, pw)
        self.client.connect(uri, port=port)

    def __del__(self):
        self.client.disconnect()

    def publish(self, type, id, key, val):
        type = type.replace(" ", "_")
        topic = "{}/{}/{}".format(type, id, key)
#        print(f"{topic}: {val}")
        self.client.publish(topic, str(val))


def getAPI():
    with urllib.request.urlopen('http://localhost:8080/api/dynamic/') as r:
       txt = r.read()
       return json.loads(txt)

def parseBatteries(data):
    out = {}
    for i, battery in enumerate(data):
        out[f"{i}_soc"] = battery['66']['soc']
        out[f"{i}_v"] = f"{(battery['66']['volts'] / 1000):.3f}"
        out[f"{i}_amps"] = f"{(battery['66']['current'] / 100):.2f}"
    return out

while True:
    sleep(4)
    try:
        src = getAPI()
        inverter = src["inverter"]

        data = {
            "inverter": {
                "mode": vevor_modes[inverter[Vevor.WORKING_MODE.value]],
                "output_volts": inverter[Vevor.OUTPUT_VOLTS.value] / 10,
                "output_pow": inverter[Vevor.OUTPUT_ACTIVE_POW.value],
                "grid_volts": inverter[Vevor.GRID_VOLTS.value] / 10,
                "grid_pow": inverter[Vevor.GRID_POWER.value],
                "solar_volts": inverter[Vevor.PV_VOLTS.value] / 10,
                "solar_pow": inverter[Vevor.PV_POWER.value],
                "solar_amps": inverter[Vevor.PV_AMPS.value] / 10,
                "battery_volts": inverter[Vevor.BATTERY_VOLTS.value] / 10,
                "battery_pow_out": -inverter[Vevor.BATTERY_POWER.value] if inverter[Vevor.BATTERY_POWER.value] < 0 else 0,
                "battery_amps_out": -(inverter[Vevor.BATTERY_AMPS.value] / 10) if inverter[Vevor.BATTERY_AMPS.value] < 0 else 0,
                "battery_pow_charge": inverter[Vevor.BATTERY_POWER.value] if inverter[Vevor.BATTERY_POWER.value] > 0 else 0,
                "battery_amps_charge": (inverter[Vevor.BATTERY_AMPS.value] / 10)  if inverter[Vevor.BATTERY_AMPS.value] > 0 else 0
            },
            "analogData": src["analogData"],
            "batteries": parseBatteries(src["batteries"]),
            "batteryPack": {
                "PERCENT":           src["batteryPack"][Coil.PERCENT.value],
                "TEMP":              src["batteryPack"][Coil.TEMP.value],
                "PACK_VOLT":         src["batteryPack"][Coil.PACK_VOLT.value] /100,
                "PACK_AMPS_OUT":   (-src["batteryPack"][Coil.PACK_AMPS.value] /100) if src["batteryPack"][Coil.STATE.value] == 1 else 0,
                "PACK_AMPS_IN":     (src["batteryPack"][Coil.PACK_AMPS.value] /100) if src["batteryPack"][Coil.STATE.value] == 2 else 0,
                "PACK_POWER_OUT":  (-src["batteryPack"][Coil.PACK_POWER.value] /10) if src["batteryPack"][Coil.STATE.value] == 1 else 0,
                "PACK_POWER_IN":    (src["batteryPack"][Coil.PACK_POWER.value] /10) if src["batteryPack"][Coil.STATE.value] == 2 else 0,
                "PACK_ENERGY":       src["batteryPack"][Coil.PACK_ENERGY.value] /100,
                "CAPACITY":          src["batteryPack"][Coil.CAPACITY.value] /1000,
                "STATE":             src["batteryPack"][Coil.STATE.value]
            }
        }

    except:
        continue

    try:
        client = MqttClient(mqtt_conf.host, mqtt_conf.port, mqtt_conf.user, mqtt_conf.pwd)
        for g, a in data.items():
            for k, v in a.items():
                client.publish("pv", g, k, v)

    except Exception as e:
        print("MQTT exception:\n{}".format(str(e)))
