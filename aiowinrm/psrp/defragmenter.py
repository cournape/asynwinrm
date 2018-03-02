import base64

import struct
from aiowinrm.psrp.fragment import Fragment
from aiowinrm.psrp.message import Message
from aiowinrm.psrp.ps_output_decoder import PsOutputDecoder


def test_bit(int_type, offset):
    mask = 1 << offset
    return (int_type & mask)


class MessageDefragmenter(object):

    @classmethod
    def fragment_from(cls, byte_string):
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
        end_start = byte_string[16]
        return Fragment(
            object_id=struct.unpack('Q', byte_string[:8][::-1]),
            fragment_id=struct.unpack('Q', byte_string[8:16][::-1]),
            end_fragment=test_bit(end_start, 1),
            start_fragment=test_bit(end_start, 0),
            blob=byte_string[21:]
        )

    @classmethod
    def message_from(cls, byte_string):
        """
        def message_from(byte_string)
            Message.new(
              '00000000-0000-0000-0000-000000000000',
              byte_string[4..7].unpack('V')[0],
              byte_string[40..-1],
              '00000000-0000-0000-0000-000000000000',
              byte_string[0..3].unpack('V')[0]
            )
        end

        :param byte_string:
        :return:
        """
        return Message(
            runspace_pool_id='00000000-0000-0000-0000-000000000000',
            message_type=struct.unpack('<I', byte_string[4:8])[0],
            data=byte_string[40:].decode('utf-8'),
            pipeline_id='00000000-0000-0000-0000-000000000000',
            destination=struct.unpack('<I', byte_string[0:4])[0]
        )

    @classmethod
    def streams_to_fragments(cls, streams):
        for steam_type, stream_data in streams:
            stream_bytes = base64.b64decode(stream_data)
            yield steam_type, cls.fragment_from(stream_bytes)

    @classmethod
    def streams_to_messages(cls, streams):
        stream_messages = {}
        cur_message_bytes = None
        for stream_type, fragment in cls.streams_to_fragments(streams):
            if stream_type not in stream_messages:
                stream_messages[stream_type] = []

            if fragment.start_fragment:
                cur_message_bytes = fragment.blob
            else:
                cur_message_bytes += fragment.blob

            if fragment.end_fragment:
                message = cls.message_from(cur_message_bytes)
                decoded = PsOutputDecoder.decode(message)
                stream_messages[stream_type].append(decoded)

        for stream_type, messages in stream_messages.items():
            if messages:
                yield stream_type, [message for message in messages if message]