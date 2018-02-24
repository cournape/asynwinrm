"""
# encoding: UTF-8
#
# Copyright 2016 Matt Wrock <matt@mattwrock.com>
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

require_relative 'fragment'

module WinRM
  # PowerShell Remoting Protcol module
  module PSRP
    # PowerShell Remoting Protocol message fragmenter.
    class MessageFragmenter
      DEFAULT_BLOB_LENGTH = 32_768

      def initialize(max_blob_length = DEFAULT_BLOB_LENGTH)
        @object_id = 0
        @max_blob_length = max_blob_length || DEFAULT_BLOB_LENGTH
      end

      attr_reader :object_id
      attr_accessor :max_blob_length

      def fragment(message)
        @object_id += 1
        message_bytes = message.bytes
        bytes_fragmented = 0
        fragment_id = 0
        fragment = nil

        while bytes_fragmented < message_bytes.length
          last_byte = bytes_fragmented + max_blob_length
          last_byte = message_bytes.length if last_byte > message_bytes.length
          fragment = Fragment.new(
            object_id,
            message.bytes[bytes_fragmented..last_byte - 1],
            fragment_id,
            bytes_fragmented == 0,
            last_byte == message_bytes.length
          )
          fragment_id += 1
          bytes_fragmented = last_byte
          yield fragment if block_given?
        end

        fragment
      end
    end
  end
end

"""
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
    def messages_to_fragments(cls, messages):
        fm = Fragmenter()
        fragments = []
        for message in messages:
            for fragment in fm.make_fragments(message):
                fragments.append(fragment)
        return fragments

    @classmethod
    def fragments_to_bytes(cls, fragments):
        return b''.join(fragment.get_bytes() for fragment in fragments)

    @classmethod
    def messages_to_fragment_bytes(cls, messages):
        return cls.fragments_to_bytes(cls.messages_to_fragments(messages))
