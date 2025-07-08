#!/usr/bin/env python3

from pprint import pprint
import pymodbus.client as modbusClient
from pymodbus.pdu import ModbusPDU
from pymodbus.datastore import ModbusSlaveContext
from time import sleep
import struct

def setup_client():
    return modbusClient.ModbusTcpClient(
        "192.168.31.190",
        port="4021",
        framer="rtu",
        timeout=100.0,
        retries=3,
        reconnect_delay=1,
        reconnect_delay_max=10,
    )

    return client

def readInputRegs(client, base, amount):
    print('Read')
    resp = client.read_input_registers(base, count=amount, slave=1)
    for i in range(0, len(resp.registers)):
        print(f"{base + i:02} {resp.registers[i]}")
    return resp.registers

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


def main():
    client = setup_client()
    client.register(SetChargeLevelResponse)
    client.connect()
#    req = SetChargeLevelRequest(1, 0xf)
    #resp = client.execute(False, req)
    #print(resp.values)

    #exit(0)
    print("holding")
#    writeHoldingReg(client, 1, 0x3)
#    writeHoldingReg(client, 2, 0x1CE0)

#    writeHoldingReg(client, 1, 0x1)
#    writeHoldingReg(client, 2, 0xA678)
#    req = SetChargeLevelRequest(1, 0x0)
#    resp = client.execute(False, req)
#    sleep(2)
    #capacity = 205000
#    capacity = 240000
#    r1 = capacity >> 16
#    r2 = capacity & 0xFFFF
#    writeHoldingReg(client, 1, r1)
#    writeHoldingReg(client, 2, r2)
#    writeHoldingReg(client, 3, 27950)



#    regs = readHoldingRegs(client, 1, 2)
#    val = regs[1] + (regs[0] << 16)
#    print(f"{val/1000:.3f}")
#    writeHoldingReg(client, 4, 2200)
    regs = readHoldingRegs(client, 0, 12)
    print(f"ADDRESS        {regs[0]}")
    print(f"CAPACITY       {(regs[1] << 16) + regs[2]}")
    print(f"CHARGE_FULL_V  {regs[3]}")
    print(f"CHARGE_EMPTY_V {regs[4]}")
    print(f"OVER_VOLT      {regs[5]}")
    print(f"OVER_AMPS      {regs[6]}")
    print(f"OVER_TEMP      {regs[7]}")
    print(f"UNDER_VOLT     {regs[8]}")
    print(f"LOW_PERCENT    {regs[9]}")

#    print("input")
    regs = readInputRegs(client, 0, 12)
#    val = regs[1] + (regs[0] << 16)
#    print(f"{val/100:.2f}")

    client.close()

if __name__ == "__main__":
    main()
