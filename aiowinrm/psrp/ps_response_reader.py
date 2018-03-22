from aiowinrm.psrp.defragmenter import MessageDefragmenter
from aiowinrm.psrp.messagedata.message_data import MessageData
from aiowinrm.psrp.messagedata.pipeline_host_call import PipelineHostCall
from aiowinrm.psrp.messagedata.pipeline_state import PipelineState, PipelineStateEnum
from aiowinrm.psrp.messagedata.runspacepool_state import \
    RunspacePoolStateEnum, RunspacePoolState
from aiowinrm.psrp.messagedata.session_capability import SessionCapability
from aiowinrm.psrp.ps_output_decoder import StreamTypeEnum, PsOutputDecoder
from aiowinrm.soap.protocol import get_streams, parse_command_done


class PsResponseReader(object):
    """
    Takes in wsmv messages and turns them into std_out, std_err, exit_code
    Will also keep track of opened/closed stated
    """

    def __init__(self, on_max_blob_len):
        self.std_out = []
        self.std_err = []
        self.exit_code = None
        self._on_max_blob_len = on_max_blob_len
        self._opened = False
        self._closed = False

    def read_wsmv_message(self, message_node):
        soap_stream_gen = get_streams(message_node)
        command_done, exit_code = parse_command_done(message_node)
        if command_done:
            self._closed = True
            self.exit_code = exit_code

        for soap_stream_type, messages in MessageDefragmenter.streams_to_messages(soap_stream_gen):
            assert soap_stream_type == 'stdout'
            for decoded_message in messages:
                assert isinstance(decoded_message, MessageData)
                # print(decoded_message.raw)
                if isinstance(decoded_message, RunspacePoolState):
                    if decoded_message.runspace_state == RunspacePoolStateEnum.OPENED:
                        self._opened = True
                    elif decoded_message.runspace_state == RunspacePoolStateEnum.CLOSED:
                        self._closed = True
                elif isinstance(decoded_message, PipelineState):
                    if decoded_message.pipeline_state in (PipelineStateEnum.FAILED,
                                                          PipelineStateEnum.DISCONNECTED,
                                                          PipelineStateEnum.STOPPED,
                                                          PipelineStateEnum.COMPLETED):
                        self._closed = True
                elif isinstance(decoded_message, PipelineHostCall):
                    self.exit_code = decoded_message.exit_code
                elif isinstance(decoded_message, SessionCapability):
                    proto_version = tuple(map(int, decoded_message.protocol_version.split('.')))
                    max_blob_length = 512000 if proto_version > (2, 1) else 153600
                    self._on_max_blob_len(max_blob_length)
                # elif not isinstance(decoded_message, PipelineOutput):
                #    pass
                stream = PsOutputDecoder.get_stream(decoded_message)
                if stream:
                    if stream.stream_type == StreamTypeEnum.STD_OUT:
                        self.std_out.append(stream.text)
                    elif stream.stream_type == StreamTypeEnum.STD_ERR:
                        self.std_err.append(stream.text)

    def get_response(self):
        std_out = self.std_out
        std_err = self.std_err
        exit_code = self.exit_code
        self.std_out = []
        self.std_err = []
        self.exit_code = None
        return '\r\n'.join(std_out), '\r\n'.join(std_err), exit_code

    @property
    def opened(self):
        return self._opened

    @property
    def exited(self):
        if self.exit_code is not None:
            return True
        return self._closed