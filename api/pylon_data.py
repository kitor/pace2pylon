from .typing import *

from threading import Semaphore

class LockableData:
    """
    Simple class with shared lock using semaphore
    """
    @classmethod
    def init(cls):
        cls.semaphore = Semaphore()

    @classmethod
    def lock(cls, timeout=None):
        return cls.semaphore.acquire(timeout)

    @classmethod
    def unlock(cls):
        return cls.semaphore.release()

    @classmethod
    def as_dict(cls):
        return {k:v for k,v in vars(cls).items() \
            if not k.startswith("_") and k != "semaphore" \
            and not isinstance(v, classmethod)}

class AnalogData(LockableData):
    """
    Data for AnalogInfo from Pylontech protocol
    """
    @classmethod
    def init(cls):
        super().init()
        cls.reset()

    @classmethod
    def reset(cls):
        cls.average_voltage         = None
        cls.total_current           = None
        cls.soc                     = None
        cls.cycles_avg              = None
        cls.cycles_max              = None
        cls.soh_avg                 = None
        cls.soh_min                 = None
        cls.cell_v_max              = None
        cls.cell_v_max_id           = None
        cls.cell_v_min              = None
        cls.cell_v_min_id           = None
        cls.cell_temp_avg           = None
        cls.cell_temp_max           = None
        cls.cell_temp_max_id        = None
        cls.cell_temp_min           = None
        cls.cell_temp_min_id        = None
        cls.mosfet_temp_avg         = None
        cls.mosfet_temp_max         = None
        cls.mosfet_temp_max_id      = None
        cls.mosfet_temp_min         = None
        cls.mosfet_temp_min_id      = None
        cls.bms_temp_avg            = None
        cls.bms_temp_max            = None
        cls.bms_temp_max_id         = None
        cls.bms_temp_min            = None
        cls.bms_temp_min_id         = None
        cls.data_ready              = False

    @classmethod
    def render(cls):
        return  f"Current: {cls.total_current/100:.02f}A       Cycles: avg {cls.cycles_avg}, max {cls.cycles_max}\n" \
                f"Health: {cls.soh_avg} (min {cls.soh_min}),   Charge: {cls.soc}%,     Battery V {cls.average_voltage/1000:.03}\n" \
                f"Cell Volt:             max ({cls.cell_v_max_id:04x}){cls.cell_v_max/1000:.03f}, min ({cls.cell_v_min_id:04x}){cls.cell_v_min/1000:.03f}\n" \
                f"Cell Temp: avg {toCelsius(cls.cell_temp_avg)/10:.01f},   max ({cls.cell_temp_max_id:04x}){toCelsius(cls.cell_temp_max)/10:.01f},  min ({cls.cell_temp_min_id:04x}){toCelsius(cls.cell_temp_min)/10:.01f}\n" \
                f"MOS  Temp: avg {toCelsius(cls.mosfet_temp_avg)/10:.01f},   max ({cls.mosfet_temp_max_id:04x}){toCelsius(cls.mosfet_temp_max)/10:.01f},  min ({cls.mosfet_temp_min_id:04x}){toCelsius(cls.mosfet_temp_min)/10:.01f}\n" \
                f"BMS  Temp: avg {toCelsius(cls.bms_temp_avg)/10:.01f},   max ({cls.bms_temp_max_id:04x}){toCelsius(cls.bms_temp_max)/10:.01f},  min ({cls.bms_temp_min_id:04x}){toCelsius(cls.bms_temp_min)/10:.01f}\n"


class PylonChargeFlags:
    CHARGE_ENABLE    = 0b10000000
    DISCHARGE_ENABLE = 0b01000000
    STRONG_CHARGE    = 0b00100000  # IDK what that means
    FULL_CHARGE      = 0b00010000  # Seems to also disable discharge when enabled

class ChargeDischargeData(LockableData):
    """
    Data for ChargeDiscargeManagement from Pylontech protocol
    """
    @classmethod
    def init(cls):
        super().init()
        cls.reset()

    @classmethod
    def reset(cls):
        cls.upper_limit     = None
        cls.lower_limit     = None
        cls.max_charge      = None
        cls.max_discharge   = None
        cls.state_flags     = 0x0   # Disable charge/discharge by default
        cls.data_ready      = False

    @classmethod
    def render(cls):
        return f"Max Charge voltage     {cls.upper_limit/1000:.3f}\n" \
               f"Max Discharge voltage  {cls.lower_limit/1000:.3f}\n" \
               f"Max Charge current     {cls.max_charge/10:.1f}\n" \
               f"Max Discharge current: {cls.max_discharge/10:.1f}\n" \
               f"State flags:           {cls.state_flags:8b}\n"

data_mapping = {
    0x61: AnalogData,
    0x63: ChargeDischargeData
}

AnalogData.init()
ChargeDischargeData.init()