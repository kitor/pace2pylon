from ui import *

import pymodbus.client as modbusClient
from api.typing import toSigned
from time import sleep
from enum import Enum
import json

from threading import Semaphore

# https://github.com/HotNoob/PythonProtocolGateway/blob/main/protocols/eg4/eg4_3000ehv_v1.holding_registry_map.csv
# https://powerforum.co.za/topic/28937-vevor-3500w-offgrid-solar-inverter/page/2/
# + a bit of own research
class Vevor(Enum):
    FAULT_CODE_1 = 100
    FAULT_CODE_2 = 101
    WARN_CODE_1 = 108
    WARN_CODE_2 = 109
    WORKING_MODE = 201
    GRID_VOLTS = 202
    GRID_FREQ = 203
    GRID_POWER = 204
    INV_VOLTS = 205
    INV_AMPS = 206
    INV_FREQ = 207
    INV_POWER = 208
    INV_CHARGING_POWER = 209
    OUTPUT_VOLTS = 210
    OUTPUT_AMPS = 211
    OUTPUT_FREQ = 212
    OUTPUT_ACTIVE_POW = 213
    OUTPUT_APPARENT_POW = 214
    BATTERY_VOLTS = 215
    BATTERY_AMPS = 216
    BATTERY_POWER = 217
    PV_VOLTS = 219
    PV_AMPS = 220
    PV_POWER = 223
    PV_CHARGING_POWER = 224
    LOAD = 225
    DCDC_TEMP = 226
    INVERTER_TEMP = 227
    MPPT_TEMP = 228
    BATTERY_SOC = 229
    BATTERY_AMPS2 = 232              # same as 21?
    INV_CHARGING_AMPS = 233          # Wrong. On grid charge >0, on off grid seems to be difference between real and reactive power
    PV_CHARGING_AMPS = 234
    SET_OUTPUT_PRIO = 301            # Program 01, 0 USB, 1 SUB, 2 SBU
    SET_BATTERY_CHARGE_PRIO = 331    # Program 16, 1 PV prio, 2 PV and Util, 3 PV only
    SET_BATTERY_CHARGE_AMPS = 332    # Program 02, min 300 (30A). Only for no-comm.
    SET_BATTERY_SOC_LOW = 341        # Program 43
    SET_BATTERY_SOC_HIGH = 342       # Program 44
    SET_BATTERY_SOC_CUTOFF = 343     # Program 45
    SET_BATTERY_DISCHARGE_PROT_AMPS = 351 # Program 46 / max discharge current protection
    #?? = 355                        # ?? / ????, value 90. Maybe program 47 / OP2 warning, via Anenji 6200W?
    #?? = 356                        # Program 48 / ???? no docs in manual
    SET_REMOTE_SHUTDOWN = 420        # remote power off, 0 OFF 1 ON

    # 761-765 ~= Pylon response to 0x63 / getChargeDiscargeManagement for first battery
    # Can't write those, ends with exception.
    LI_STATE_FLAGS = 760            # Different representation than Pylon uses
    LI_MAX_VOLTS = 761
    LI_MIN_VOLTS = 762
    LI_MAX_CHARGE_AMPS = 763
    LI_MAX_DISCHARGE_AMPS = 764     # just amps without minus sign; ignored by inverter anyway

    # 770-775 ~= Pylon response to 0x61 / getAnalogInfo for first battery
    LI_VOLTS = 770
    # ?? = 772 # shows 65535 / -1 all the time
    LI_SOC = 773
    LI_AMPS = 775

    @classmethod
    def as_dict(cls):
        return {i.name: i.value for i in cls}

inverterData = []

# vevor modbus protocol
class VevorInverter:
    instance = None

    def __init__(self, thread_id, addr, port, slave):
        self.thread_id = thread_id
        self.slave = slave
        self.semaphore = Semaphore()
        self.client = modbusClient.ModbusTcpClient(
            addr,
            port=port,
            framer="rtu",
            timeout=100.0,
            retries=3,
            reconnect_delay=1,
            reconnect_delay_max=10,
        )

        # init data
        for i in range(0,800):
            inverterData.append(0)

    def runComm(self):
        while True:
            try:
                self.client.connect()
                while True:
                    self.gatherData()
                self.client.close()
            except Exception as e:
                tprint(self.thread_id, "vevor modbus error")
                tprint(self.thread_id, str(e))

    def gatherData(self):
        resp = self.__readRegs(200, 35)
        resp = self.__readRegs(301, 1)
        resp = self.__readRegs(330, 20)
        resp = self.__readRegs(420, 1)
        resp = self.__readRegs(760, 20)

        tprint(self.thread_id, "vevor read done")
        sleep(1)

    def setOutputMode(self, mode):
        if mode not in [0,1,2]: # Program 01, 0 USB, 1 SUB, 2 SBU
            return
        # Prevent unnecessary writes
        if inverterData[Vevor.SET_OUTPUT_PRIO.value] != mode:
            tprint(self.thread_id, f"vevor setOutputMode {mode}")
            self.__writeReg(Vevor.SET_OUTPUT_PRIO.value, mode)

    def setChargingPriority(self, mode):
        if mode not in [1,2,3]: #1 PV prio, 2 PV and Util, 3 PV only
            return

        # Prevent unnecessary writes
        if inverterData[Vevor.SET_BATTERY_CHARGE_PRIO.value] != mode:
            tprint(self.thread_id, f"vevor toggleChargingPriority {mode}")
            self.__writeReg(Vevor.SET_BATTERY_CHARGE_PRIO.value, mode)

    def __readRegs(self, base, amount):
        self.semaphore.acquire()
        try:
            resp = self.client.read_holding_registers(
                    base, count=amount, slave = self.slave)
        except:
            pass
        self.semaphore.release()

        if not resp:
            return False

        for idx, value in enumerate(resp.registers):
            inverterData[base+idx] = toSigned(value)

        return True

    def __writeReg(self, reg, val):
        self.semaphore.acquire()
        try:
            resp = self.client.write_registers(reg, values=[val], slave=self.slave)
        except:
            pass
        self.semaphore.release()

        return resp


# Mock for testing purposes
class VevorMock:
    def __init__(self, thread_id, addr, port, slave):
        self.thread_id = thread_id

        # init data
        for i in range(0,800):
            inverterData.append(0)

    def runComm(self):
        tprint(self.thread_id, "hello mock")
        self.setFakeData()

        while True:
            self.updateFakeData()
            sleep(1) # fake thread

    def setFakeData(self):
        # just a few needed for Maestro to work:
        inverterData[Vevor.SET_OUTPUT_PRIO.value] = 2 # SBU
        inverterData[Vevor.SET_BATTERY_CHARGE_PRIO.value] = 3 # PV only
        inverterData[Vevor.SET_BATTERY_SOC_LOW.value] = 30
        inverterData[Vevor.SET_BATTERY_SOC_HIGH.value] = 60
        inverterData[Vevor.SET_BATTERY_SOC_CUTOFF.value] = 5
        inverterData[Vevor.SET_BATTERY_CHARGE_AMPS.value] = 600 # 60A

    def updateFakeData(self):
        from api.pylon_data import AnalogData as AD, ChargeDischargeData as CDD
        from translator import Translator, get_avg
        # Pull some plausible values from Translator
        try:
            inverterData[Vevor.BATTERY_VOLTS.value] = int(AD.average_voltage / 100)
            inverterData[Vevor.BATTERY_AMPS.value] = int(AD.total_current / 1000)
            inverterData[Vevor.BATTERY_SOC.value] = int(get_avg(Translator.stats["soc"]))
            inverterData[Vevor.LI_MAX_CHARGE_AMPS.value] = int(CDD.max_charge * 10)
        except:
            pass

    def setOutputMode(self, mode):
        if mode not in [0,1,2]: # Program 01, 0 USB, 1 SUB, 2 SBU
            return
        if inverterData[Vevor.SET_OUTPUT_PRIO.value] != mode:
            tprint(self.thread_id, f"vevor setOutputMode {mode}")
            inverterData[Vevor.SET_OUTPUT_PRIO.value] = mode

    def setChargingPriority(self, mode):
        if mode not in [1,2,3]: #1 PV prio, 2 PV and Util, 3 PV only
            return
        if inverterData[Vevor.SET_BATTERY_CHARGE_PRIO.value] != mode:
            tprint(self.thread_id, f"vevor toggleChargingPriority {mode}")
            inverterData[Vevor.SET_BATTERY_CHARGE_PRIO.value] = mode
