#!/usr/bin/env python3

from pprint import pprint
import pymodbus.client as modbusClient

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

def readRegs(client, base, amount):
    print('Read')
    resp = client.read_holding_registers(base, count=amount, slave=1)
    for i in range(0, len(resp.registers)):
        print(f"{base + i:02} {resp.registers[i]}")
    return resp.registers

def writeReg(client, reg, val):
    print('Write')
    resp = client.write_registers(reg, values=[val], slave=1)
    return resp
    print(resp)

# regs
"""
301 - output priority, 0 USB, 1 SUB, 2 SBU
331 - battery charge priority, 1 PV prio, 2 PV and Util, 3 PV only

341 - 43 / SOC back to utility
342 - 44 / SOC back to battery
343 - 45 / SOC low dc cutoff

351 - 46 / max discharge current protection in "single" program 28?
355 - ?? / ????, value 90
356 - 48 / ???? no docs in manual

420 - remote power off, 0 OFF, 1 ON
"""
def main():
    client = setup_client()
    client.connect()

    #regs = readRegs(client, 341, 1)
    regs = readRegs(client, 300, 30)
    #next = 1
    # if regs[0] == 1:
    #    next = 3
    #writeReg(client, 332, 300)
    #print(f"Write: {next}")
    #resp = writeReg(client, 310, 0)
    #pprint(resp.registers)
    #print("Read")
    #regs = readRegs(client, 310, 1)
    #writeReg(client, 420, int(not(regs[0])) )
    #readRegs(client, 420, 1)

    client.close()

if __name__ == "__main__":
    main()
