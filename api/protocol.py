from textwrap import indent
from enum import Enum

from .typing import *
from ui import *

class FrameType(Enum):
    UNKNOWN = 0
    REQUEST = 1
    RESPONSE = 2

def computeChecksum(payload):
    # sum payload bytes, mod 65535, invert, add 1
    CHK = ((sum(payload) % 65535) ^ 0xFFFF ) + 1
    return toUShort(CHK)


def computeLength(inf):
    if not inf:
        return b'\x30\x30\x30\x30' #0000

    LENID = len(inf) & 0x0FFF # has to be < 4095 bytes but whatever

    # To calculate LCHKSUM: D11D10D9D8+D7D6D5D4+D3D2D1D0
    L3 = LENID >> 8 & 0xF
    L2 = LENID >> 4 & 0xF
    L1 = LENID      & 0xF
    SUM = L3 + L2 + L1

    # modulus 16 take remainder, then do a bitwise invert and then plus 1.
    LCHKSUM = ((SUM % 16) ^ 0xF) + 1

    # LCHKSUM at high bytes, LENID at low
    LENGTH = LENID + (LCHKSUM << 12)
    return(toUShort(LENGTH))



class Protocol:
    """
    Pace protocol frame representation
    Takes care of encoding/decoding frames, excl. actual command payload.

    Payload de/encoding is delegated to InfoObj.
    """
    def __init__(self, SOI, VER, ADR, CID1, CID2, LENGTH, INFO,
            CHKSUM, EOI, InfoObj, type):
        self.SOI       = SOI
        self.VER       = VER
        self.ADR       = ADR
        self.CID1      = CID1
        self.CID2      = CID2
        self.LENGTH    = LENGTH
        self.INFO      = INFO
        self.CHKSUM    = CHKSUM
        self.EOI       = EOI
        self.InfoObj   = InfoObj
        self.type      = type

    @staticmethod
    def decodeResponse(frame, InfoObj = None):
        SOI     = frame[0:1]
        VER     = frame[1:3]
        ADR     = frame[3:5]
        CID1    = frame[5:7]
        CID2    = frame[7:9]
        LENGTH  = frame[9:13]
        INFO    = frame[13:-5]
        CHKSUM  = frame[-5:-1]
        EOI     = frame[-1:]

        payload = VER + ADR + CID1 + CID2 + LENGTH + INFO

        chk = computeChecksum(payload)
        if chk != CHKSUM:
            #print(f"ERR: chksum doesn't match! {CHKSUM} {chk}")
            return False

        return InfoObj.decodeResponse(INFO)

    @staticmethod
    def decodeRequest(frame, mapping):
        SOI     = frame[0:1]
        VER     = frame[1:3]
        ADR     = frame[3:5]
        CID1    = frame[5:7]
        CID2    = frame[7:9]
        LENGTH  = frame[9:13]
        INFO    = frame[13:-5]
        CHKSUM  = frame[-5:-1]
        EOI     = frame[-1:]

        payload = VER + ADR + CID1 + CID2 + LENGTH + INFO

        chk = computeChecksum(payload)
        if chk != CHKSUM:
            # Payload checksum doesn't match
            return False

        len = computeLength(INFO)
        if len != LENGTH:
            # Data checksum doesn't match
            return False

        InfoObj = None
        cmd_id = fromUShort(CID2)
        if cmd_id in mapping.keys():
            InfoObj = mapping[cmd_id]

        return Protocol(SOI, VER, ADR, CID1, CID2, LENGTH, INFO,
                CHKSUM, EOI, InfoObj(), FrameType.REQUEST)


    def create(ADR, InfoObj, type = FrameType.RESPONSE, Pace=False):
        if not InfoObj:
            return None

        if type == FrameType.RESPONSE:
            INFO = InfoObj.response()
            CID2 = InfoObj.CID2_resp
        else:
            INFO = InfoObj.request()
            CID2 = InfoObj.CID2_cmd

        SOI = b'\x7E'         # ~
        EOI = b'\x0D'         # CR

        VER = b'\x32\x30'     # 20h, old / pylon proto
        if Pace:
            VER = b'\x32\x35' # 25h, new / pace proto
        CID1 = b'\x34\x36'    # 46h, battery data

        LENGTH = computeLength(INFO)

        payload = VER + ADR + CID1 + CID2 + LENGTH + INFO
        CHKSUM = computeChecksum(payload)

        return Protocol(SOI, VER, ADR, CID1, CID2, LENGTH, INFO, CHKSUM, EOI,
                    InfoObj, type)


    def encode(self):
        return self.SOI + self.VER + self.ADR + self.CID1 + self.CID2 \
                + self.LENGTH + self.INFO + self.CHKSUM + self.EOI


    def printInfo(self, prefix, thread_id):
        hdr = "Unknown FrameType!"
        response = ""

        if self.InfoObj:
            if self.type == FrameType.REQUEST:
                hdr = self.InfoObj.renderRequest()
            elif self.type == FrameType.RESPONSE:
                hdr = "response:"
                response = self.InfoObj.renderResponse()

        tprint(thread_id, f"{prefix} ADR {fromByte(self.ADR):02x}, CID2 {fromByte(self.CID2):02x} {hdr}")
        if response:
            tprint(thread_id, indent(response, " "*(len(prefix)+3)))

    def renderInfo(self, prefix):
        hdr = "Unknown FrameType!"
        response = ""

        if self.InfoObj:
            if self.type == FrameType.REQUEST:
                hdr = self.InfoObj.renderRequest()
            elif self.type == FrameType.RESPONSE:
                hdr = "response:"
                response = self.InfoObj.renderResponse()

        buf = f"{prefix} ADR {fromByte(self.ADR):02x}, CID2 {fromByte(self.CID2):02x} {hdr}"
        if response:
            buf += "\n" + indent(response, " "*(len(prefix)+3))
        return buf