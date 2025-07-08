#!/usr/bin/env -S python3
import socket

from api.protocol import Protocol, FrameType
from api.pace import *
import argparse

# For easy commands testing
parser = argparse.ArgumentParser()
parser.add_argument("CID2", help="command id for CID2")
parser.add_argument("msg", help="Ascii response to decode")
args = parser.parse_args()

command = int(args.CID2, 16)

InfoObj = mapping[command]()
msg = args.msg.encode() + b'\x0D'
print(msg)
Protocol.decodeResponse(msg, InfoObj)
print(InfoObj.renderResponse())