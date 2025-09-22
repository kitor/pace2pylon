from ui import *

import pymodbus.client as modbusClient
from pymodbus.pdu import ModbusPDU
from pymodbus.datastore import ModbusSlaveContext

from time import sleep
from enum import Enum
import json, struct

from threading import Semaphore


# Holding registers
class CoilSettings(Enum):
    ADDRESS        = 0
    CAPACITY_HI    = 1
    CAPACITY_LO    = 2 # HI+LO, 3 dec
    CHARGE_FULL_V  = 3 # 2 dec
    CHARGE_EMPTY_V = 4 # 2 dec
    OVER_VOLT      = 5 # 2 dec
    OVER_AMPS      = 6 # 2 dec
    OVER_TEMP      = 7
    UNDER_VOLT     = 8 # 2 dec
    LOW_PERCENT    = 9

    @classmethod
    def as_dict(cls):
        return {i.name: i.value for i in cls}


class Coil(Enum):
    # CoilFields, sainitized from split fields
    PERCENT     = 0
    TEMP        = 1  # deg C
    PACK_VOLT   = 2  # 2 dec
    PACK_AMPS   = 3  #
    PACK_POWER  = 5  # 1 dec
    PACK_ENERGY = 7  # 2 dec, Wh
    CAPACITY    = 9  # mAh
    FLAGS       = 10
    STATE       = 11 # -> CoilChargeState
    @classmethod
    def as_dict(cls):
        return {i.name: i.value for i in cls}


# Input registers
class CoilFields(Enum):
    PERCENT         = 0
    TEMP            = 1  # deg C
    PACK_VOLT       = 2  # 2 dec
    PACK_AMPS       = 3  #
    PACK_POWER_HI   = 4
    PACK_POWER_LO   = 5  # 1 dec
    PACK_ENERGY_HI  = 6
    PACK_ENERGY_LO  = 7  # 2 dec, Wh
    CAPACITY_LO     = 8
    CAPACITY_HI     = 9  # mAh
    FLAGS           = 10
    STATE           = 11 # -> CoilChargeState


class CoilChargeState(Enum):
    STATE_IDLE      = 0
    STATE_DISCHARGE = 1
    STATE_CHARGE    = 2

    @classmethod
    def as_dict(cls):
        return {i.name: i.value for i in cls}


class SetChargeLevelResponse(ModbusPDU):
    function_code = 0x6F
    rtu_byte_count_pos = 2

    def __init__(self, values=None, slave=1, transaction=0):
        super().__init__(dev_id=slave, transaction_id=transaction)
        self.values = values or []

    def encode(self):
        return struct.pack('>HH', 0, self.value)

    def decode(self, data):
        a, val = struct.unpack('>HH', data)
        self.values = [val]


class SetChargeLevelRequest(ModbusPDU):
    function_code = 0x6F
    rtu_frame_size = 8

    def __init__(self, slave=1, value=0, transaction=0):
        super().__init__(dev_id=slave, transaction_id=transaction)
        self.value = value

    def encode(self):
        return struct.pack('>HH', 0, self.value)

    def decode(self, data):
        a, self.value = struct.unpack('>HH', data)

    async def update_datastore(self, context: ModbusSlaveContext) -> ModbusPDU:
        """Execute."""
        _ = context
        return SetChargeLevelResponse()


class CoilData:
    values = []
    comm = False


class CoilState:
    instance = None

    def __init__(self, thread_id, addr, port, slave):
        self.thread_id = thread_id
        self.slave = slave
        self.semaphore = Semaphore()
        self.client = modbusClient.ModbusTcpClient(
            addr,
            port=port,
            framer="rtu",
            timeout=10.0,
            retries=3,
            reconnect_delay=1,
            reconnect_delay_max=10,
        )

        # init data
        for i in range(0,12):
            CoilData.values.append(0)


    def task(self):
        tprint(self.thread_id, "Coil: task start")
        while True:
            try:
                self.client.connect()
                self.client.register(SetChargeLevelResponse)
                while True:
                    sleep(1)
                    self.gatherData()
                self.client.close()
            except Exception as e:
                tprint(self.thread_id, "Coil: modbus exception: " + str(e))
                CoilData.comm = False


    def gatherData(self):
        self.semaphore.acquire()
        read_ok = True
        try:
            resp = self.client.read_input_registers(
                    0, count=12, slave = self.slave)
        except:
            read_ok = False
        self.semaphore.release()

        if not resp or read_ok:
            tprint(self.thread_id, f"Coil: read failure ({read_ok})")
            CoilData.comm = False
            return

        CoilData.values[0] = resp.registers[0]
        CoilData.values[1] = resp.registers[1]
        CoilData.values[2] = resp.registers[2]
        CoilData.values[3] = resp.registers[3]
        CoilData.values[5] = resp.registers[5] + (resp.registers[4] << 16)
        CoilData.values[7] = resp.registers[7] + (resp.registers[6] << 16)
        CoilData.values[9] = resp.registers[9] + (resp.registers[8] << 16)
        CoilData.values[10] = resp.registers[10]
        CoilData.values[11] = resp.registers[11]
        CoilData.comm = True


    def setFull(self):
        self.semaphore.acquire()
        try:
            req = SetChargeLevelRequest(1, 0xF)
            resp = self.client.execute(False, req)
        except:
            tprint(self.thread_id, f"Coil: setFull exception: " + str(e))
        self.semaphore.release()

        tprint(self.thread_id, "Coil: set full")


    def setEmpty(self):
        self.semaphore.acquire()
        try:
            req = SetChargeLevelRequest(1, 0x0)
            resp = self.client.execute(False, req)
        except:
            tprint(self.thread_id, f"Coil: setEmpty exception: " + str(e))
        self.semaphore.release()

        tprint(self.thread_id, "Coil: set empty")


    def writeFullCapacityAndVoltage(self, capacity, voltage):
        r1 = capacity >> 16
        r2 = capacity & 0xFFFF

        self.semaphore.acquire()
        try:
            self.client.write_registers(1, [r1, r2, voltage], slave=self.slave)
        except:
            tprint(self.thread_id, f"Coil: writeFullCapacityAndVoltage exception: " + str(e))
        self.semaphore.release()

        tprint(self.thread_id, f"Coil: set capacity {capacity/1000}Ah, {voltage/100}V")


class CoilMock:
    def __init__(self, thread_id, addr, port, slave):
        self.thread_id = thread_id
        self.slave = slave
        from config import Thresholds
        self.capacity = Thresholds.pack_capacity
        self.currentCapacity = Thresholds.pack_capacity

        # init data
        for i in range(0,12):
            CoilData.values.append(0)


    def task(self):
        tprint(self.thread_id, "mock Coil: task start")

        while True:
            self.updateFakeData()
            sleep(1) # fake thread


    def updateFakeData(self):
        from api.pylon_data import AnalogData as AD, ChargeDischargeData as CDD
        from translator import Translator, get_avg
        # Pull some plausible values from Translator
        try:
            CoilData.values[0] = int(get_avg(Translator.stats["soc"]))
            CoilData.values[1] = int(AD.cell_temp_avg / 10)
            CoilData.values[2] = int(AD.average_voltage / 10)
            CoilData.values[3] = int(AD.total_current / 10)
            CoilData.values[5] = CoilData.values[2] * CoilData.values[3]
            CoilData.values[7] = int((self.currentCapacity  * CoilData.values[2]/1000) * (CoilData.values[0]/100)) 
            CoilData.values[9] = self.currentCapacity
            CoilData.values[10] = 0
            CoilData.values[11] = 0
        except:
            pass

        CoilData.comm = True


    def setFull(self):
        from config import Thresholds
        self.capacity = self.currentCapacity
        tprint(self.thread_id, "mock Coil: set full")


    def setEmpty(self):
        self.capacity = 0
        tprint(self.thread_id, "mock Coil: set empty")


    def writeFullCapacityAndVoltage(self, capacity, voltage):
        self.capacity = capacity
        self.currentCapacity = capacity
        tprint(self.thread_id, f"mock Coil set capacity {capacity/1000}Ah, {voltage/10}V")
