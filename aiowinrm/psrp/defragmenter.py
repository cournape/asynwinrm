import base64

import struct
from aiowinrm.psrp.fragment import Fragment


class MessageDefragmenter(object):

    def __init__(self, messages):
        self.messages = messages

    def defragment(self, base64_bytes):
        fragment = self.fragment_from(base64.b64decode(base64_bytes))


    def fragment_from(self, byte_string):
        """
        def fragment_from(byte_string)
            Fragment.new(
              byte_string[0..7].reverse.unpack('Q')[0],
              byte_string[21..-1].bytes,
              byte_string[8..15].reverse.unpack('Q')[0],
              byte_string[16].unpack('C')[0][0] == 1,
              byte_string[16].unpack('C')[0][1] == 1
            )
        end

        :param byte_string:
        :return:
        """

        # :object_id, :fragment_id, :end_fragment, :start_fragment, :blob
        end_start = struct.unpack('c', byte_string[16])[0]
        return Fragment(
            object_id=struct.unpack('Q', byte_string[:7][::-1]),
            fragment_id=struct.unpack('Q', byte_string[8:15][::-1]),
            end_fragment=(end_start % 0b10 == 0),
            start_fragment=(end_start % 0b1 == 0),
            blob=byte_string[21:]
        )