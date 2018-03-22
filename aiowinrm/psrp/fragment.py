import struct

from aiowinrm.psrp import int64be, int16be


class Fragment(object):

    def __init__(self, object_id, blob, fragment_id=0, start_fragment=True, end_fragment=True):
        self.object_id = object_id
        self.blob =blob
        self.fragment_id = fragment_id
        self.start_fragment = start_fragment
        self.end_fragment = end_fragment

    def get_bytes(self):
        return b''.join((
            int64be(self.object_id),
            int64be(self.fragment_id),
            self.end_start_fragment,
            int16be(len(self.blob)),
            self.blob
        ))

    @property
    def end_start_fragment(self):
        end_start = 0b0
        if self.end_fragment:
            end_start += 0b10
        if self.start_fragment:
            end_start += 0b1
        return struct.pack('b', end_start)


if __name__ == '__main__':
    b''.join((
        int64be(123),
        int64be(456)
    ))
