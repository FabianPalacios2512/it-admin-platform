import struct
length = 500
header = bytearray([0x81])
header.append(126 | 0x80)
header.extend(struct.pack('>H', length))
print([hex(x) for x in header])
