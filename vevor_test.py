#!/usr/bin/env python3

from pprint import pprint
import pymodbus.client as modbusClient
from pymodbus.pdu import ModbusPDU
from pymodbus.datastore import ModbusSlaveContext

import struct

def setup_client():
    return modbusClient.ModbusTcpClient(
        "192.168.31.190",
        port="4025",
        framer="rtu",
        timeout=100.0,
        retries=3,
        reconnect_delay=1,
        reconnect_delay_max=10,
    )

    return client


def readHoldingRegs(client, base, amount):
    print('Read')
    resp = client.read_holding_registers(base, count=amount, slave=1)
    for i in range(0, len(resp.registers)):
        print(f"{base + i:02} {resp.registers[i]:08x}")
    return resp.registers

def writeHoldingReg(client, reg, val):
    print('Write')
    resp = client.write_registers(reg, values=[val], slave=1)
    return resp
    print(resp)

#SET_OUTPUT_PRIO = 301            # Program 01, 0 USB, 1 SUB, 2 SBU
#SET_BATTERY_CHARGE_PRIO = 331    # Program 16, 1 PV prio, 2 PV and Util, 3 PV only
#SET_BATTERY_SOC_LOW = 341        # Program 43
#SET_BATTERY_SOC_HIGH = 342       # Program 44
#SET_BATTERY_SOC_CUTOFF = 343     # Program 45

def main():
    client = setup_client()
    client.connect()

    #exit(0)
    print("holding")
    reg = 301
    val = 0
    writeHoldingReg(client, reg, val)
    regs = readHoldingRegs(client, reg, 1)
#    writeHoldingReg(client, 341, 30)
#    writeHoldingReg(client, 342, 60)
#    writeHoldingReg(client, 343, 5)
    client.close()

if __name__ == "__main__":
    main()
