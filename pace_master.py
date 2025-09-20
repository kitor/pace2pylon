from api.protocol import Protocol, FrameType
from api.pace import *
from api.typing import *
from ui import *

import socket
from time import sleep

import queue

pace_instances = []

class PaceMaster:
    def __init__(self, thread_id, addr, port):
        self.thread_id = thread_id
        self.conn_data = (addr, port)
        self.queue = queue.Queue(maxsize=32)

    def thread(self):
        while True:
            try:
                self.runComm()
            except socket.error:
                tprint(self.thread_id, "Socket error")
            except Exception as e:
                tprint(self.thread_id, f"Exception in PaceMaster thread {self.thread_id}")
                tprint(self.thread_id, str(e))

    def runComm(self):
        self.flushIncomingData()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1) # BMS shall repsond very quickly
            s.connect(self.conn_data)
            while True:
                cmd, args, cbr = None, None, None
                try:
                    cmd, args, cbr = self.queue.get(timeout=1)
                    cid2, data = self.__execute(s, cmd, args);

                    self.queue.task_done()
                    cbr(self.thread_id, cid2, data)
                except socket.error:
                    # Return result with failed status
                    self.queue.task_done()
                    cbr(self.thread_id, None, None, failed=True)
                    raise # force reconnect
                except queue.Empty:
                    # that's fine
                    pass


    def tryPostMsg(self, cmd, cbr, params = {}):
        try:
            self.queue.put((cmd, params, cbr), timeout=1)
        except queue.Full:
            # bounce to CBR with failed flag
            cbr(self.thread_id, None, None, failed=True)


    def flushIncomingData(self):
        # In case we reset comm or received response that failed to decode
        # (likely buffer processed out of order)
        # flush all data from buffer
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1) # BMS shall repsond very quickly
                s.connect(self.conn_data)
                msg = s.recv(4096)
        except socket.timeout as e:
            pass

        tprint(self.thread_id, "flush done")


    def __execute(self, s, cmd, args):
        InfoObj = cmd(**args)
        req = Protocol.create(b"\x30\x30", InfoObj, FrameType.REQUEST)
        req.printInfo(" <-- ", self.thread_id)
        s.send(req.encode())

        msg = b'' # empty buffer
        try:
            loops = 0
            while True:
                if loops > 20:
                    raise TimeoutError
                msg += s.recv(4096)
                if msg[-1:] == b'\r':
                    break
                loops += 1
        except socket.timeout:
            tprint(self.thread_id, "socket timeout, skipping command")
            raise

        return self.decodeResponse(msg, InfoObj)

    def decodeResponse(self, msg, InfoObj):
        response = False
        try:
            response = Protocol.decodeResponse(msg, InfoObj)
            tprint(self.thread_id, InfoObj.renderResponse())
            return fromUShort(InfoObj.CID2_cmd), InfoObj.data
        except Exception as e:
            tprint(self.thread_id, f"Exception during decoding\n{str(msg)}\n{str(e)}")
            raise # something went wrong, force flush and restart
