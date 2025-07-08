from api.protocol import Protocol, FrameType
from api.pylon import *
from api.typing import *
from ui import *

import socket

class PylonSlave:
    def __init__(self, thread_id, addr, port):
        self.thread_id = thread_id
        self.conn_data = (addr, port)
        self.responses = {}
        self.reqObj = mapping.values()

    def runComm(self):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3) # Inverter talks every second or so
                    s.connect(self.conn_data )
                    self.doComm(s)
            except socket.error:
                tprint(self.thread_id, "Socket error")
            except Exception as e:
                tprint(self.thread_id, f"Exception in PylonSlave thread {self.thread_id}")
                tprint(self.thread_id, str(e))

    def doComm(self, s):
        while True:
            msg = b'' # empty buffer
            try:
                while True:
                    msg += s.recv(2048)
                    if msg[-1:] == b'\r':
                        break
            except socket.timeout:
                tprint(self.thread_id, "socket timeout, nothing to dispatch")
                continue
            else:
                resp = self.dispatch(msg)
                msg = b''
                if resp:
                    s.send(resp)


    def dispatch(self, frame):
        frame = Protocol.decodeRequest(frame, mapping)

        if not frame:
            return False # Decode failed, no response

        if not fromByte(frame.ADR) == 0x2:
            return False # We respond to inverter first expected slave address

        frame.printInfo(" -- > ", self.thread_id)

        CID2 = fromByte(frame.CID2)
        locked = data_mapping[CID2].lock(0.2)
        if locked and data_mapping[CID2].data_ready:
            # Respond only if data is marked as ready.
            resp = Protocol.create(ADR = frame.ADR, InfoObj=frame.InfoObj)
            data_mapping[CID2].unlock()
            if resp:
                resp.printInfo(" < -- ", self.thread_id)
                return resp.encode()

        return False