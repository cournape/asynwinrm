from aiowinrm.psrp import int16le, uuid_to_windows_guid_bytes, BYTE_ORDER_MARK


class Message(object):

    # Value of message destination when sent to a client
    CLIENT_DESTINATION = 1

    # Value of message destination when sent to a server
    SERVER_DESTINATION = 2

    MESSAGE_TYPES = {
        'session_capability': 0x00010002,
        'init_runspacepool': 0x00010004,
        'public_key': 0x00010005,
        'encrypted_session_key': 0x00010006,
        'public_key_request': 0x00010007,
        'connect_runspacepool': 0x00010008,
        'runspace_init_data': 0x0002100b,
        'reset_runspace_state': 0x0002100c,
        'set_max_runspaces': 0x00021002,
        'set_min_runspaces': 0x00021003,
        'runspace_availability': 0x00021004,
        'runspacepool_state': 0x00021005,
        'create_pipeline': 0x00021006,
        'get_available_runspaces': 0x00021007,
        'user_event': 0x00021008,
        'application_private_data': 0x00021009,
        'get_command_metadata': 0x0002100a,
        'runspacepool_host_call': 0x00021100,
        'runspacepool_host_response': 0x00021101,
        'pipeline_input': 0x00041002,
        'end_of_pipeline_input': 0x00041003,
        'pipeline_output': 0x00041004,
        'error_record': 0x00041005,
        'pipeline_state': 0x00041006,
        'debug_record': 0x00041007,
        'verbose_record': 0x00041008,
        'warning_record': 0x00041009,
        'progress_record': 0x00041010,
        'information_record': 0x00041011,
        'pipeline_host_call': 0x00041100,
        'pipeline_host_response': 0x00041101
    }

    def __init__(self, runspace_pool_id, message_type, data, pipeline_id=None, destination=SERVER_DESTINATION):
        if message_type not in self.__class__.MESSAGE_TYPES:
            raise Exception(f'invalid message type: {message_type}')
        assert isinstance(data, str)
        self.runspace_pool_id = runspace_pool_id
        self.message_type = self.__class__.MESSAGE_TYPES[message_type]
        self.data = data
        self.pipeline_id = pipeline_id
        self.destination = destination

    def get_bytes(self):
        """
        def bytes
            [
              int16le(destination),
              int16le(type),
              uuid_to_windows_guid_bytes(runspace_pool_id),
              uuid_to_windows_guid_bytes(pipeline_id),
              byte_order_mark,
              data_bytes
            ].flatten
          end
        :return:
        """
        return b''.join((
            int16le(self.destination),
            int16le(self.message_type),
            uuid_to_windows_guid_bytes(self.runspace_pool_id),
            uuid_to_windows_guid_bytes(self.pipeline_id),
            BYTE_ORDER_MARK,
            self.data.encode('utf-8')
        ))
