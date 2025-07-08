#!/usr/bin/env -S python3
import socket

from api.protocol import Protocol, FrameType
from api.pace import *
import argparse

# For easy commands testing
parser = argparse.ArgumentParser()
parser.add_argument("battery_id", help="battery id")
parser.add_argument("CID2", help="command id for CID2")
args = parser.parse_args()

IP = '192.168.20.101'
bms_port = [ 2, 4, 6, 8, 10, 12, 38, 40, 42, 44, 46, 48]
port = 4000 + bms_port[int(args.battery_id)]
command = int(args.CID2, 16)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(1) # BMS shall repsond very quickly
    s.connect((IP, port))

    #InfoObj = mapping[command]()
    InfoObj = ReadCellBalancingConfiguration()
    #InfoObj = WriteCellBalancingConfiguration()
#    InfoObj = WriteFullChargeLowChargeConfiguration()
#    InfoObj = WriteDischargeMosfetSwitchCommand()
#    InfoObj = WriteShutdownCommand()
#    InfoObj = PackStatus()
    req = Protocol.create(b"\x30\x30", InfoObj, FrameType.REQUEST, Pace=True)
    print(req.encode())
    print(req.renderInfo(" <-- "))
    print("===")
    s.send(req.encode())

    msg = b'' # empty buffer
    try:
        while True:
            msg += s.recv(4096)
            if msg[-1:] == b'\r':
                break
    except socket.timeout:
        print("socket timeout, aborting")
        exit(1);

    print(msg)
    response = Protocol.decodeResponse(msg, InfoObj)
    print(InfoObj.renderResponse())
