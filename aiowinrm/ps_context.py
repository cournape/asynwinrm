import uuid

from aiowinrm.errors import SoapTimeout, AIOWinRMException
from aiowinrm.psrp.fragmenter import Fragmenter
from aiowinrm.psrp.messages import \
    create_session_capability_message, init_runspace_pool_message, \
    create_pipeline_message
from aiowinrm.psrp.ps_response_reader import PsResponseReader
from aiowinrm.soap.protocol import \
    create_power_shell_payload, parse_create_shell_response, get_ps_response, \
    command_output, close_shell_payload, create_ps_pipeline, parse_create_command_response, \
    create_send_payload
from aiowinrm.winrm_connection import WinRmConnection


EXIT_CODE_CODE = "\r\nif (!$?) { if($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }"


class PowerShellContext(object):

    def __init__(self, session, host):
        self._session = session

        self.host = host
        self.session_id = uuid.uuid4()
        self.runspace_id = uuid.uuid4()
        self.shell_id = None

        self._max_blob_length = None
        self._win_rm_connection = None
        self._shell_timed_out = False

        self._ps_reader = PsResponseReader(self._on_max_blob_len)

    def _on_max_blob_len(self, max_blob_length):
        self._max_blob_length = max_blob_length

    @property
    def _creation_payload(self):
        compat_msg = create_session_capability_message(self.runspace_id)
        runspace_msg = init_runspace_pool_message(self.runspace_id)
        creation_payload = Fragmenter.messages_to_fragment_bytes(
            messages=[compat_msg, runspace_msg],
            max_blob_length=self._max_blob_length)
        return creation_payload

    async def __aenter__(self):
        try:
            payload = create_power_shell_payload(self.runspace_id, self.session_id, self._creation_payload)
            self._win_rm_connection = WinRmConnection(self._session, self.host)
            response = await self._win_rm_connection.request(payload)
            self.shell_id = parse_create_shell_response(response)

            get_ps_response_payload = get_ps_response(self.shell_id, self.session_id)
            while not self._ps_reader.opened and not self._ps_reader.exited:
                # print('requesting')
                response = await self._win_rm_connection.request(get_ps_response_payload)
                self._ps_reader.read_wsmv_message(response)

            return self
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def start_script(self, script):
        try:
            self._check_pipeline_state()
            script += EXIT_CODE_CODE
            command_id = uuid.uuid4()
            message = create_pipeline_message(self.runspace_id, command_id, script)
            # print(message)
            for fragment in Fragmenter.messages_to_fragments([message], self._max_blob_length):
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

    def _check_pipeline_state(self):
        if not self._ps_reader.opened:
            raise AIOWinRMException('Pipeline not yet opened')
        if self._ps_reader.exited:
            raise AIOWinRMException('Pipeline already exited')

    async def get_command_output(self, command_id):
        try:
            self._check_pipeline_state()
            payload = command_output(self.shell_id, command_id, power_shell=True)
            data = await self._win_rm_connection.request(payload)
            self._ps_reader.read_wsmv_message(data)
            return self._ps_reader.get_response()
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def __aexit__(self, ex=None, *a, **kw):
        self._ps_reader = None
        if not self._win_rm_connection:
            return
        if self.shell_id is None and ex is None:
            await self._win_rm_connection.close()
            raise RuntimeError("__aexit__ called without __aenter__")

        if isinstance(ex, SoapTimeout):
            payload = close_shell_payload(self.shell_id, power_shell=True)
            await self._win_rm_connection.request(payload)
        await self._win_rm_connection.close()