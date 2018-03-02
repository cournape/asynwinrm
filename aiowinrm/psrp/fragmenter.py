from aiowinrm.psrp.fragment import Fragment
from aiowinrm.psrp.message import Message


class Fragmenter(object):

    DEFAULT_BLOB_LENGTH = 32768

    def __init__(self, max_blob_length=DEFAULT_BLOB_LENGTH):
        self.object_id = 0
        self.max_blob_length = max_blob_length

    def make_fragments(self, message):
        if isinstance(message, Message):
            message_bytes = message.get_bytes()
        elif isinstance(message, bytes):
            message_bytes = message
        else:
            raise Exception("Unexpected message type")

        self.object_id += 1
        byte_cnt = len(message_bytes)
        bytes_fragmented = 0
        fragment_id = 0

        while bytes_fragmented < byte_cnt:
            last_byte = bytes_fragmented + self.max_blob_length
            if last_byte > byte_cnt:
                last_byte = byte_cnt
            fragment = Fragment(
                object_id=self.object_id,
                blob=message_bytes[bytes_fragmented:last_byte - 1],
                fragment_id=fragment_id,
                start_fragment=bytes_fragmented == 0,
                end_fragment=last_byte == byte_cnt
            )
            fragment_id += 1
            bytes_fragmented = last_byte
            yield fragment

    @classmethod
    def messages_to_fragments(cls, messages, max_blob_length):
        fm = Fragmenter()
        if max_blob_length is not None:
            fm.max_blob_length = max_blob_length
        fragments = []
        for message in messages:
            for fragment in fm.make_fragments(message):
                fragments.append(fragment)
        return fragments

    @classmethod
    def fragments_to_bytes(cls, fragments):
        return b''.join(fragment.get_bytes() for fragment in fragments)

    @classmethod
    def messages_to_fragment_bytes(cls, messages, max_blob_length):
        return cls.fragments_to_bytes(
            cls.messages_to_fragments(messages, max_blob_length))
