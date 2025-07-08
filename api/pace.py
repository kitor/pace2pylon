from .typing import *
from .apiFrame import *

# https://github.com/nkinnan/esphome-pace-bms/blob/main/components/pace_bms/pace_bms_protocol_v25.h
# I'm simplifying things a bit since I know I connect to each battery separately
# thus there will be no more than one in a chain

class WriteShutdownCommand(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x39\x43'  # 9Ch
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        inf  = toUShort("01")  # Unknown per esphome docs, possibly command id?
        return inf

    def decodeResponse(self, INFO):
        print(INFO)
        self.data = True
        return True

    def renderRequest(self):
        return "WriteShutdownCommand()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"    Response received"

class WriteFullChargeLowChargeConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x41\x45'  # AEh
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        INFO  = toUShort("27950")
        INFO += toUShort("500")
        INFO += toByte("10")
        self.data = {
            "full_mv": fromUShort(INFO[0:4]),
            "full_ma": fromUShort(INFO[4:8]),
            "low_percent": fromUShort(INFO[8:10]),
        }
        return INFO

    def decodeResponse(self, INFO):
        print(INFO)
        return True

    def renderRequest(self):
        return "WriteFullChargeLowChargeConfiguration()" \
                f"Full mv {self.data["full_mv"]}, ma {self.data["full_ma"]}\n" \
                f"Low % {self.data["low_percent"]}"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return "Response received"

class ReadFullChargeLowChargeConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x41\x46'  # AFh
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        print(INFO)
        self.data = {
            "full_mv": fromUShort(INFO[0:4]),
            "full_ma": fromUShort(INFO[4:8]),
            "low_percent": fromUShort(INFO[8:10]),
        }
        return True

    def renderRequest(self):
        return "ReadFullChargeLowChargeConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"Full mv {self.data["full_mv"]}, ma {self.data["full_ma"]}\n" \
               f"Low % {self.data["low_percent"]}"

class WriteCellOverVoltageConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x44\x30'  # D0h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        INFO  = toByte("01")
        INFO += toUShort("3600")
        INFO += toUShort("3700")
        INFO += toUShort("3400")
        INFO += toByte("10")
        self.data = {
            "alarm_mv": fromUShort(INFO[2:6]),
            "prot_mv": fromUShort(INFO[6:10]),
            "prot_release_mv": fromUShort(INFO[10:14]),
            "prot_delay_ms": fromUShort(INFO[14:16]),
        }
        return INFO

    def decodeResponse(self, INFO):
        print(INFO)

        return True

    def renderRequest(self):
        return "WriteCellOverVoltageConfiguration()" \
                f"Alarm {self.data["alarm_mv"]}, prot {self.data["prot_mv"]}\n" \
                f"Release mv {self.data["prot_release_mv"]}, Release ms {self.data["prot_delay_ms"] * 100}"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return "Response received"


class ReadCellOverVoltageConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x44\x31'  # D1h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        print(INFO)
        self.data = {
            "alarm_mv": fromUShort(INFO[2:6]),
            "prot_mv": fromUShort(INFO[6:10]),
            "prot_release_mv": fromUShort(INFO[10:14]),
            "prot_delay_ms": fromUShort(INFO[14:16]),
        }
        return True

    def renderRequest(self):
        return "ReadCellOverVoltageConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"Alarm {self.data["alarm_mv"]}, prot {self.data["prot_mv"]}\n" \
               f"Release mv {self.data["prot_release_mv"]}, Release ms {self.data["prot_delay_ms"] * 100}"

class WriteDischargeMosfetSwitchCommand(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x39\x42'  # 9Bh
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        inf  = toUShort("00")
        return inf

    def decodeResponse(self, INFO):
        print(INFO)
        self.data = True
        return True

    def renderRequest(self):
        return "WriteDischargeMosfetSwitchCommand()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"    Response received"


class ReadCellBalancingConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x42\x36'  # B6h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        print(INFO)
        self.data = {
            "threshold_mv": fromUShort(INFO[0:4]),
            "delta_mv": fromUShort(INFO[4:8]),
        }
        return True

    def renderRequest(self):
        return "ReadCellBalancingConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"Threshold {self.data["threshold_mv"]}, delta {self.data["delta_mv"]}"


class WriteCellBalancingConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x42\x35'  # B5h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        inf  = toUShort("3300")
        inf += toUShort("20")
        self.data = {
            "threshold_mv": fromUShort(inf[0:4]),
            "delta_mv": fromUShort(inf[4:8]),
        }
        return inf

    def decodeResponse(self, INFO):
        return True

    def renderRequest(self):
        return f"getPackOverVoltageConfiguration()\n" \
               f"Threshold {self.data["threshold_mv"]}, delta {self.data["delta_mv"]}"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return "Response received"


class ReadPackOverVoltageConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x44\x35'  # D5h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        self.data = {
            "upper_volts": fromUShort(INFO[2:6])
        }
        return True

    def renderRequest(self):
        return "getPackOverVoltageConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"OverVolt alarm: {self.data["upper_volts"]/1000}V"


class ReadPackUnderVoltageConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b"\x44\x37"  # D7h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        self.data = {
            "lower_volts": fromUShort(INFO[2:6])
        }
        return True

    def renderRequest(self):
        return "getPackUnderVoltageConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"UnderVolt alarm: {self.data["lower_volts"]/1000}V"


class ReadChargeOverCurrentConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b"\x44\x39"  # D9h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        self.data = {
            "charge_amps": fromUShort(INFO[2:6])
        }
        return True

    def renderRequest(self):
        return "getChargeOverCurrentConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"ChargeOC alarm: {self.data["charge_amps"]}A"


class ReadDischargeSlowOverCurrentConfiguration(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b"\x44\x42"  # DBh
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.data = None

    def request(self):
        return b''

    def decodeResponse(self, INFO):
        self.data = {
            "discharge_amps": fromShort(INFO[2:6])
        }
        return True

    def renderRequest(self):
        return "getDischargeSlowOverCurrentConfiguration()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"DischargeOC alarm {self.data["discharge_amps"]}A"

class ReadPackStatus(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b'\x34\x34'  # 44h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error

        self.battery_number = 255     # ask for all batteries
        self.data = None

    def request(self):
        return toByte(self.battery_number)

    def __decodeCells(self, INFO):
        cells = fromUShort(INFO[0:2])
        byte = 2
        data = []
        for i in range (0, cells):
            cell = fromUShort(INFO[byte:byte+2])
            data.append(cell)
            byte += 2
        return data, byte

    def __decodeTemps(self, INFO):
        temps = fromUShort(INFO[0:2])
        byte = 2
        data = []
        for i in range (0, temps):
            temp = fromUShort(INFO[byte:byte+2])
            data.append(temp)
            byte += 2
        return data, byte

    def decodeResponse(self, INFO):
        # skipped packs step since it is single pack anyway
        bus_id = fromUShort(INFO[2:4])
        INFO = INFO[4:]
        cells, cells_len = self.__decodeCells(INFO)
        INFO = INFO[cells_len:]
        temps, temps_len = self.__decodeTemps(INFO)
        INFO = INFO[temps_len:]
        self.data = {
            "cells": cells,
            "temps": temps,
            "charge_amps"      : fromUShort(INFO[0:2]),
            "total_voltage"    : fromUShort(INFO[2:4]),
            "discharge_amps"   : fromUShort(INFO[4:6]),
            "protect_state_1"  : fromUShort(INFO[6:8]),
            "protect_state_2"  : fromUShort(INFO[8:10]),
            "system_state"     : fromUShort(INFO[10:12]),
            "control_state"    : fromUShort(INFO[12:14]), # | 0xEF, # mask Current limit function disabled as my BMS doesn't support it
            "fault_state"      : fromUShort(INFO[14:16]),
            "balance_state_1"  : fromUShort(INFO[16:18]),
            "balance_state_2"  : fromUShort(INFO[18:20]),
            "warn_state_1"     : fromUShort(INFO[20:22]),
            "warn_state_2"     : fromUShort(INFO[22:24])
        }

        return True

    def renderRequest(self):
        return "getPackStatus()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"
        return f"  Prot1 { self.data["protect_state_1"] } Prot2 { self.data["protect_state_2"] }\n" \
               f"  Sys   { self.data["system_state"] } Ctrl  { self.data["control_state"] }\n" \
               f"  Fault { self.data["fault_state"] }\n" \
               f"  Warn1 { self.data["warn_state_1"] } Warn2 { self.data["warn_state_2"] }\n" \
               f"  Bal1  { self.data["balance_state_1"] } Bal2 { self.data["balance_state_2"] }"

class ReadAnalogData(ApiFrame):
    def __init__(self):
        self.CID2_cmd  = b"\x34\x32"  # 42h
        self.CID2_resp = b"\x30\x30"  # 00h -> no error
        self.battery_number = 255     # ask for all batteries

        self.data = None

    def request(self):
        return toByte(self.battery_number)

    def __decodePack(self, INFO):
        cells, cells_len = self.__decodeCells(INFO)
        INFO = INFO[cells_len:]

        temps, temps_len = self.__decodeTemps(INFO)
        INFO = INFO[temps_len:]

        cap_remaining = fromUShort(INFO[8:12])
        cap_full = fromUShort(INFO[14:18])
        self.data = {
            "cells": cells,
            "cell_v_max": max(cells),
            "cell_v_min": min(cells),
            "temps": temps,
            "cell_temp_avg": int((temps[0] + temps[1]) / 2),
            "cell_temp_max": min(temps[0:1]),
            "cell_temp_min": max(temps[0:1]),
            "mosfet_temp": temps[2],
            "bms_temp": temps[3],
            "current": fromShort(INFO[0:4]),
            "volts": fromUShort(INFO[4:8]),
            "soc": min(int(cap_remaining/cap_full * 100), 100),
            "cycles": fromUShort(INFO[18:22]),
            "soh": 100
        }

        return cells_len + temps_len + 8

    def __decodeCells(self, INFO):
        cells = fromUShort(INFO[0:2])
        byte = 2
        data = []
        for i in range (0, cells):
            cell = fromUShort(INFO[byte:byte+4])
            data.append(cell)
            byte += 4
        return data, byte

    def __decodeTemps(self, INFO):
        temps = fromUShort(INFO[0:2])
        byte = 2
        data = []
        for i in range (0, temps):
            temp = fromUShort(INFO[byte:byte+4])
            data.append(temp)
            byte += 4
        return data, byte

    def decodeResponse(self, INFO):
        packs = fromUShort(INFO[2:4])
        INFO = INFO[4:]
        for i in range (0, packs):
            shift = self.__decodePack(INFO)
            INFO = INFO[shift:]
        return True

    def renderRequest(self):
        return "getAnalogData()"

    def renderResponse(self):
        if not self.data:
            return f"    Data not decoded yet"

        return f"   Cells: {', '.join(f'{x/1000:.03f}' for x in self.data["cells"])}\n" \
               f"   Temps: {', '.join(f'{toCelsius(x)/10:.01f}' for x in self.data["temps"])}\n" \
               f"   Pack {self.data["soc"]}% @{self.data["volts"]/1000:.3f}V; {self.data["current"]/100:.02f}A; {self.data["cycles"]} cycles"


mapping = {
    0x42: ReadAnalogData,
    0x44: ReadPackStatus,
    0xD5: ReadPackOverVoltageConfiguration,
    0xD7: ReadPackUnderVoltageConfiguration,
    0xD9: ReadChargeOverCurrentConfiguration,
    0xDB: ReadDischargeSlowOverCurrentConfiguration
}
