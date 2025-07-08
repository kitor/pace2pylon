# Some functions to decode/encode this stupid mostly hex over ascii format

# Short and unsigned short. Two hex bytes, thus 4 ascii chars / 4 bytes
def toUShort(val):
    return bytes(bytearray(f"{int(val):04x}".upper(),'ascii'))

def toShort(val):
    if val < 0:
        val = ~(-val - 1) & 0xFFFF
    return toUShort(val)

def fromUShort(obj):
    return int(obj,16)

def fromShort(obj):
    val = fromUShort(obj)
    return toSigned(val)

def toSigned(val):
    if val > 32767:
        val = -((~val & 0xFFFF) + 1)
    return val

# Single byte, encoded as hex text. Thus 16 as it is two chars / two bytes
# In Sunsynk described as "1 byte, accurancy 0"
def fromByte(obj):
    return int(obj.decode("ascii"), 16)

def toByte(val):
    return bytes(bytearray(f"{int(val):02x}".upper(),'ascii'))


# shall those two live here?
def toKelvin(val):
    return val + 2731

def toCelsius(val):
    return val - 2731