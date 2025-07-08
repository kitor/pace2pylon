from ui import *
from api.pylon_data import AnalogData as AD, ChargeDischargeData as CDD, PylonChargeFlags
from coil import Coil, CoilData

from threading import Semaphore
from time import time, sleep

from config import Thresholds

def get_avg(list):
    return int(sum(list) / len(list))

def get_max(list):
    v = max(list)
    return v, list.index(v)

def get_min(list):
    v = min(list)
    return v, list.index(v)

class Translator:
    """
    The fun part that translates data gathered from Pace 0x25h protocol
    to Pace 0x20h protocol Pylontech variant
    """
    batteries = []
    last_update = []
    upper_limit = Thresholds.pack_charge_v  # default to "regular mode"
    stats = {
        "volts": [],
        "current": [],
        "soc": [],
        "cycles": [],
        "soh": [],
        "cell_v_max": [],
        "cell_v_min": [],
        "cell_temp_avg": [],
        "cell_temp_min": [],
        "cell_temp_max": [],
        "mosfet_temp": [],
        "bms_temp": [],
        "upper_volts": [],
        "lower_volts": [],
        "charge_amps": [],
        "discharge_amps": [],
        "battery_comm": []
    }
    prev_stats = None
    thread_id = 0

    @classmethod
    def init(cls, count):
        cls.count = count
        cls.semaphore = Semaphore()
        cls.state_flags = 0x0  # disable everything

        cls.batteries = []
        for i in range(cls.count):
            cls.batteries.append({})
            cls.last_update.append(0)

        for name in cls.stats.keys():
            cls.stats[name] = [ None ] * cls.count

    @classmethod
    def updateThread(cls):
        while True:
            sleep(1)
            cls.updateStats()

    @classmethod
    def updateStats(cls):
        tprint(cls.thread_id, "== translator start ==")


        ts = time()

        cls.semaphore.acquire()
        # Logic for timeouts moved here from feeder
        # We detect timeout ourselfs intstead of relying on feeder to notify us
        for i in range(len(cls.last_update)):
            if ts - cls.last_update[i] > 10:
                cls.stats["battery_comm"][i] = False

        try:
            # AnalogData
            for id, battery in enumerate(cls.batteries):
                if not battery:
                    continue

                if 0x42 in battery.keys():
                    cls.stats["volts"][id]          = battery[0x42]["volts"]
                    cls.stats["current"][id]        = battery[0x42]["current"]
                    cls.stats["soc"][id]            = battery[0x42]["soc"]
                    cls.stats["cycles"][id]         = battery[0x42]["cycles"]
                    cls.stats["soh"][id]            = battery[0x42]["soh"]
                    cls.stats["cell_v_max"][id]     = battery[0x42]["cell_v_max"]
                    cls.stats["cell_v_min"][id]     = battery[0x42]["cell_v_min"]
                    cls.stats["cell_temp_avg"][id]  = battery[0x42]["cell_temp_avg"]
                    cls.stats["cell_temp_min"][id]  = battery[0x42]["cell_temp_min"]
                    cls.stats["cell_temp_max"][id]  = battery[0x42]["cell_temp_max"]
                    cls.stats["mosfet_temp"][id]    = battery[0x42]["mosfet_temp"]
                    cls.stats["bms_temp"][id]       = battery[0x42]["bms_temp"]

                # ChargeDischargeData
                if 0xD5 in battery.keys():
                    cls.stats["upper_volts"][id]    = battery[0xD5]["upper_volts"]
                if 0xD7 in battery.keys():
                    cls.stats["lower_volts"][id]    = battery[0xD7]["lower_volts"]
                if 0xD9 in battery.keys():
                    cls.stats["charge_amps"][id]    = battery[0xD9]["charge_amps"]
                if 0xDB in battery.keys():
                    cls.stats["discharge_amps"][id] = battery[0xDB]["discharge_amps"]

        except Exception as e:
            # How did we get here? Pass just not to deadlock.
            # If we end here, likely some stats will be missing
            # and updatePylonData() will gracefully fail so it is fine.
            pass

        cls.updatePylonData()
        cls.semaphore.release()
        tprint(cls.thread_id, "== translator done ==")

    @classmethod
    def setBatteryData(cls, id, command, data):
        ts = time()
        cls.semaphore.acquire()
        cls.last_update[id] = ts
        cls.batteries[id][command] = data
        cls.stats["battery_comm"][id] = True
        cls.semaphore.release()

    @classmethod
    def setBatteryUpperLimit(cls, limit):
        cls.semaphore.acquire()
        try:
            if limit > 27000 and limit < min(cls.stats["upper_volts"]):
                cls.upper_limit = limit
        except:
            pass
        cls.semaphore.release()

    @classmethod
    def disableBattery(cls):
        cls.state_flags = 0x0

    @classmethod
    def toggleBatteryFullCharge(cls):
        cls.state_flags = cls.state_flags ^ PylonChargeFlags.FULL_CHARGE

    @classmethod
    def disableBatteryFullCharge(cls):
        cls.state_flags = cls.state_flags & ~PylonChargeFlags.FULL_CHARGE

    @classmethod
    def enableBatteryDischarge(cls):
        cls.state_flags = cls.state_flags | PylonChargeFlags.DISCHARGE_ENABLE

    @classmethod
    def enableBatteryCharge(cls):
        cls.state_flags = cls.state_flags | PylonChargeFlags.CHARGE_ENABLE

    @classmethod
    def disableBatteryCharge(cls):
        cls.disableBatteryFullCharge()
        cls.state_flags = cls.state_flags & ~PylonChargeFlags.CHARGE_ENABLE


    @classmethod
    def updatePylonData(cls):
        AD.lock()
        try:
            AD.reset()
            AD.average_voltage         = get_avg(cls.stats["volts"])
            AD.total_current           = sum(cls.stats["current"])
#            AD.soc                     = min(cls.stats["soc"])
            AD.soc                     = CoilData.values[0]
            AD.cycles_avg              = get_avg(cls.stats["cycles"])
            AD.cycles_max              = max(cls.stats["cycles"])
            AD.soh_avg                 = get_avg(cls.stats["soh"])
            AD.soh_min                 = min(cls.stats["soh"])
            AD.cell_temp_avg           = get_avg(cls.stats["cell_temp_avg"])
            AD.bms_temp_avg            = get_avg(cls.stats["bms_temp"])
            AD.mosfet_temp_avg         = get_avg(cls.stats["mosfet_temp"])

            AD.cell_v_max, AD.cell_v_max_id = get_max(cls.stats["cell_v_max"])
            AD.cell_v_min, AD.cell_v_min_id = get_min(cls.stats["cell_v_min"])
            AD.cell_temp_max, AD.cell_temp_max_id = get_max(cls.stats["cell_temp_max"])
            AD.cell_temp_min, AD.cell_temp_min_id = get_min(cls.stats["cell_temp_min"])
            AD.mosfet_temp_max, AD.mosfet_temp_max_id = get_max(cls.stats["mosfet_temp"])
            AD.mosfet_temp_min, AD.mosfet_temp_min_id = get_min(cls.stats["mosfet_temp"])
            AD.bms_temp_max, AD.bms_temp_max_id = get_max(cls.stats["bms_temp"])
            AD.bms_temp_min, AD.bms_temp_min_id = get_min(cls.stats["bms_temp"])
            AD.data_ready = True
        except Exception as e:
            # This can happen if complete stats are not yet initialized
            tprint(cls.thread_id, str(e))
            pass
        AD.unlock()

        CDD.lock()
        try:
            CDD.reset()
            CDD.upper_limit   = cls.upper_limit                       # allow to be set externally
            CDD.lower_limit   = max(cls.stats["lower_volts"])
            CDD.max_charge    =  8 * sum(cls.stats["charge_amps"])    # convert full amps to .0, limit to 80% of BMS limit ( *10 *0.8)
            CDD.max_discharge =  8 * sum(cls.stats["discharge_amps"]) # convert full amps to .0, limit to 80% of BMS limit ( *10 *0.8)
            CDD.state_flags   = cls.state_flags
            #CDD.state_flags   = PylonChargeFlags.CHARGE_ENABLE | PylonChargeFlags.FULL_CHARGE
            CDD.data_ready    = True
        except Exception as e:
            tprint(cls.thread_id, str(e))
            # This can happen if complete stats are not yet initialized
            pass
        CDD.unlock()
