import re
import struct
import uuid


BYTE_ORDER_MARK = bytes(bytearray((239, 187, 191)))


def int64be(int64):
    """
    [int64 >> 32, int64 & 0x00000000ffffffff].pack('N2').unpack('C8')


    return [struct.unpack('B', c)[0] for c in
            (struct.pack('>I', int64 >> 32) + struct.pack('>I', int64 & 0x00000000ffffffff))]

    :param int64:
    :return:
    """
    return struct.pack('>I', int64 >> 32) + struct.pack('>I', int64 & 0x00000000ffffffff)


def int16be(int16):
    """
    [int16].pack('N').unpack('C4')

    return [struct.unpack('B', c)[0] for c in struct.pack('>I', int16)]

    :param int16:
    :return:
    """
    return struct.pack('>I', int16)


def int16le(int16):
    """
    [int16].pack('N').unpack('C4').reverse

    :param int16:
    :return:
    """
    return struct.pack('<I', int16)


def uuid_to_windows_guid_bytes(uuid_in):
    """
    def uuid_to_windows_guid_bytes(uuid)
        return [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] unless uuid
        b = uuid.scan(/[0-9a-fA-F]{2}/).map { |x| x.to_i(16) }
        b[0..3].reverse + b[4..5].reverse + b[6..7].reverse + b[8..15]
      end
    """
    if not uuid_in:
        return b'\x00' * 16
    if isinstance(uuid_in, str):
        uuid_in = uuid.UUID(uuid_in)
    assert isinstance(uuid_in, uuid.UUID)
    return uuid_in.bytes_le


def remove_bom(text):
    return text.replace("\xef\xbb\xbf", "")


def horizontal_white_space_replace(match):
    raise NotImplementedError()


def strip_hex_white_space(text):
    # \h does not exist in python
    text = text.replace("_x000D__x000A_", "\n")
    return re.sub(r'_x(\s{4})_', horizontal_white_space_replace, text, flags=re.UNICODE)
