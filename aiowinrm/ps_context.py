import uuid

from aiowinrm.errors import SoapTimeout
from aiowinrm.psrp.defragmenter import MessageDefragmenter
from aiowinrm.psrp.fragmenter import Fragmenter
from aiowinrm.psrp.messagedata.pipeline_host_call import PipelineHostCall
from aiowinrm.psrp.messagedata.runspacepool_state import RunspacePoolStateEnum, RunspacePoolState
from aiowinrm.psrp.messagedata.session_capability import SessionCapability
from aiowinrm.psrp.messages import create_session_capability_message, init_runspace_pool_message, \
    create_pipeline_message
from aiowinrm.psrp.ps_output_decoder import StreamTypeEnum, PsOutputDecoder
from aiowinrm.soap.protocol import create_power_shell_payload, parse_create_shell_response, get_ps_response, \
    get_streams, command_output, parse_command_output, close_shell_payload, create_ps_pipeline, \
    parse_create_command_response, create_send_payload
from aiowinrm.winrm_connection import WinRmConnection


EXIT_CODE_CODE = "\r\nif (!$?) { if($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }"


class PowerShellContext(object):

    def __init__(self, session, host):
        self._session = session

        self.host = host
        self.session_id = uuid.uuid4()
        self.runspace_id = uuid.uuid4()
        self.shell_id = None

        self.std_out = []
        self.std_err = []
        self.exit_code = None
        self._win_rm_connection = None
        self._shell_timed_out = False

    async def __aenter__(self):
        try:
            compat_msg = create_session_capability_message(self.runspace_id)
            runspace_msg = init_runspace_pool_message(self.runspace_id)
            creation_payload = Fragmenter.messages_to_fragment_bytes((compat_msg, runspace_msg))

            payload = create_power_shell_payload(self.runspace_id, self.session_id, creation_payload)
            self._win_rm_connection = WinRmConnection(self._session, self.host)
            response = await self._win_rm_connection.request(payload)
            self.shell_id = parse_create_shell_response(response)

            state = RunspacePoolStateEnum.OPENING
            get_ps_response_payload = get_ps_response(self.shell_id, self.session_id)
            while state != RunspacePoolStateEnum.OPENED:
                print('requesting')
                response_root = await self._win_rm_connection.request(get_ps_response_payload)
                soap_stream_gen = get_streams(response_root)
                for soap_stream_type, messages in MessageDefragmenter.streams_to_messages(soap_stream_gen):
                    assert soap_stream_type == 'stdout'
                    for decoded_message in messages:
                        if isinstance(decoded_message, RunspacePoolState):
                            state = decoded_message.runspace_state
                        elif isinstance(decoded_message, PipelineHostCall):
                            self.exit_code = decoded_message.exit_code
                            if self.exit_code is not None:
                                print("EEEEEXXXXXIIIIIIIITTTTT")
                        elif isinstance(decoded_message, SessionCapability):
                            proto_version = tuple(map(int, decoded_message.protocol_version.split('.')))
                            max_blob_length = 512000 if proto_version > (2, 1) else 153600
                        stream = PsOutputDecoder.get_stream(decoded_message)
                        if stream:
                            if stream.stream_type == StreamTypeEnum.STD_OUT:
                                self.std_out.append(stream.text)
                            elif stream.stream_type == StreamTypeEnum.STD_ERR:
                                self.std_err.append(stream.text)

            return self
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def start_script(self, script):
        try:
            script += EXIT_CODE_CODE
            command_id = uuid.uuid4()
            message = create_pipeline_message(self.runspace_id, command_id, script)
            # print(message)
            for fragment in Fragmenter.messages_to_fragments([message]):
                if fragment.start_fragment:
                    payload = create_ps_pipeline(self.shell_id,
                                                 self.session_id,
                                                 command_id,
                                                 fragment.get_bytes())
                    data = await self._win_rm_connection.request(payload)
                    command_id = parse_create_command_response(data)
                else:
                    payload = create_send_payload(self.shell_id,
                                                  self.session_id,
                                                  command_id,
                                                  fragment.get_bytes())
                    await self._win_rm_connection.request(payload)
            return command_id
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def get_command_output(self, command_id):
        try:
            payload = command_output(self.shell_id, command_id, power_shell=True)
            data = await self._win_rm_connection.request(payload)
            parsed = parse_command_output(data)
            return None, None, 1
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def __aexit__(self, ex=None, *a, **kw):
        if not self._win_rm_connection:
            return
        if self.shell_id is None and ex is None:
            await self._win_rm_connection.close()
            raise RuntimeError("__aexit__ called without __aenter__")

        if isinstance(ex, SoapTimeout):
            payload = close_shell_payload(self.shell_id, power_shell=True)
            await self._win_rm_connection.request(payload)
        await self._win_rm_connection.close()