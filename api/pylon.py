from .typing import *
from .apiFrame import *
from .pylon_data import *
from ui import *
# From Sunsynk docs, implementing only methods that my Vevor inverter seems
# to use.

class ChargeDiscargeManagement(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x36\x33'  # 63h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def renderResponse(self, INFO = None):
        return ChargeDischargeData.render()

    def response(self):
        inf  = toUShort(ChargeDischargeData.upper_limit)
        inf += toUShort(ChargeDischargeData.lower_limit)
        inf += toUShort(ChargeDischargeData.max_charge)
        inf += toShort(ChargeDischargeData.max_discharge)
        inf += toByte(ChargeDischargeData.state_flags)
        return inf

    def renderRequest(self):
        return "getChargeDiscargeManagement()"


class AnalogInfo(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x36\x31'  # 61h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def renderResponse(self, INFO = None):
        return AnalogData.render()

    def response(self):
        inf  = toUShort(AnalogData.average_voltage)
        inf += toShort(AnalogData.total_current)
        inf += toByte(AnalogData.soc)
        inf += toUShort(AnalogData.cycles_avg)
        inf += toUShort(AnalogData.cycles_max)
        inf += toByte(AnalogData.soh_avg)
        inf += toByte(AnalogData.soh_min)
        inf += toUShort(AnalogData.cell_v_max)
        inf += toUShort(AnalogData.cell_v_max_id)
        inf += toUShort(AnalogData.cell_v_min)
        inf += toUShort(AnalogData.cell_v_min_id)
        inf += toUShort(AnalogData.cell_temp_avg)
        inf += toUShort(AnalogData.cell_temp_max)
        inf += toUShort(AnalogData.cell_temp_max_id)
        inf += toUShort(AnalogData.cell_temp_min)
        inf += toUShort(AnalogData.cell_temp_min_id)
        inf += toUShort(AnalogData.mosfet_temp_avg)
        inf += toUShort(AnalogData.mosfet_temp_max)
        inf += toUShort(AnalogData.mosfet_temp_max_id)
        inf += toUShort(AnalogData.mosfet_temp_min)
        inf += toUShort(AnalogData.mosfet_temp_min_id)
        inf += toUShort(AnalogData.bms_temp_avg)
        inf += toUShort(AnalogData.bms_temp_max)
        inf += toUShort(AnalogData.bms_temp_max_id)
        inf += toUShort(AnalogData.bms_temp_min)
        inf += toUShort(AnalogData.bms_temp_min_id)
        return inf

    def renderRequest(self):
        return "getAnalogInfo()"

mapping = {
    0x61: AnalogInfo,
    0x63: ChargeDiscargeManagement
}