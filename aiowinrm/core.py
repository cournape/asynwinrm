import uuid

import lxml.etree as etree
import sys

from aiowinrm.psrp.defragmenter import MessageDefragmenter
from aiowinrm.psrp.fragmenter import Fragmenter
from aiowinrm.psrp.messagedata.pipeline_host_call import PipelineHostCall
from aiowinrm.psrp.messagedata.session_capability import SessionCapability
from aiowinrm.psrp.messages import create_session_capability_message, init_runspace_pool_message, \
    create_pipeline_message
from aiowinrm.psrp.messagedata.runspacepool_state import RunspacePoolStateEnum, RunspacePoolState
from aiowinrm.psrp.ps_output_decoder import PsOutputDecoder, StreamTypeEnum
from .errors import AIOWinRMException
from .soap.protocol import (
    create_shell_payload, close_shell_payload, parse_create_shell_response,
    create_command, parse_create_command_response, cleanup_command,
    command_output, parse_command_output,
    create_power_shell_payload, get_ps_response, parse_soap_response, get_streams, create_ps_pipeline,
    create_send_payload, parse_create_shell_response_node, SoapTimeout)


async def _check_response_200_code(resp):
    if resp.status != 200:
        await resp.release()
        raise AIOWinRMException(
            "Unhandled http error {}".format(resp.status)
        )


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
        self._win_rm_conection = None
        self._shell_timed_out = False

    async def __aenter__(self):
        compat_msg = create_session_capability_message(self.runspace_id)
        runspace_msg = init_runspace_pool_message(self.runspace_id)
        creation_payload = Fragmenter.messages_to_fragment_bytes((compat_msg, runspace_msg))

        payload = create_power_shell_payload(self.runspace_id, self.session_id, creation_payload)
        self._win_rm_conection = WinRmConnection(self._session, self.host)
        try:
            response = await self._win_rm_conection.request(payload)
            self.shell_id = parse_create_shell_response_node(response)
            # assert self.shell_id == self.runspace_id
            state = RunspacePoolStateEnum.OPENING
            get_ps_response_payload = get_ps_response(self.shell_id, self.session_id)
            while state != RunspacePoolStateEnum.OPENED:
                print('requesting')
                response_root = await self._win_rm_conection.request(get_ps_response_payload)
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
                                print(stream.text)
                                self.std_out.append(stream.text)
                            elif stream.stream_type == StreamTypeEnum.STD_ERR:
                                print(stream.text, sys.stderr)
                                self.std_err.append(stream.text)

            return self
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def start_script(self, script):
        try:
            script += "\r\nif (!$?) { if($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }"
            command_id = uuid.uuid4()
            message = create_pipeline_message(self.runspace_id, command_id, script)
            # print(message)
            for fragment in Fragmenter.messages_to_fragments([message]):
                if fragment.start_fragment:
                    payload = create_ps_pipeline(self.shell_id, self.session_id, command_id, fragment.get_bytes())
                    print(etree.tostring(payload, pretty_print=True).decode('utf-8'))
                    data = await self._win_rm_conection.request(payload)
                    command_id = parse_create_command_response(data)
                else:
                    payload = create_send_payload(self.shell_id, self.session_id, command_id, fragment.get_bytes())
                    await self._win_rm_conection.request(payload)
            return command_id
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def get_command_output(self, command_id):
        payload = command_output(self.shell_id, command_id, power_shell=True)
        data = await self._win_rm_conection.request(payload)
        parsed = parse_command_output(data)
        return None, None, 1


    async def __aexit__(self, ex=None, *a, **kw):
        if not self._win_rm_conection:
            return
        if self.shell_id is None and ex is None:
            await self._win_rm_conection.close()
            raise RuntimeError("__aexit__ called without __aenter__")

        if isinstance(ex, SoapTimeout):
            payload = close_shell_payload(self.shell_id, power_shell=True)
            await self._win_rm_conection.request(payload)
        await self._win_rm_conection.close()


class ShellContext(object):
    def __init__(self, session, host, env=None, cwd=None):
        self._session = session

        self.host = host

        self.env = env
        self.cwd = cwd

        self.shell_id = None

    async def __aenter__(self):
        payload = etree.tostring(create_shell_payload(self.env, self.cwd))

        resp = await _make_winrm_request(
            self._session, self.host, payload
        )
        if resp.status == 401:
            await resp.release()
            raise AIOWinRMException(
                "Unauthorized {}".format(resp.status)
            )
        if resp.status != 200:
            await resp.release()
            raise AIOWinRMException(
                "Unhandled http error {}".format(resp.status)
            )

        try:
            data = await resp.text()
            self.shell_id = parse_create_shell_response(data)
            return self
        finally:
            await resp.release()

    async def __aexit__(self, *a, **kw):
        if self.shell_id is None:
            raise RuntimeError("__aexit__ called without __aenter__")

        payload = etree.tostring(close_shell_payload(self.shell_id))
        resp = await _make_winrm_request(self._session, self.host, payload)
        await resp.release()


class CommandContext(object):
    def __init__(self, session, host, shell_id, command, args=()):
        self._session = session

        self.host = host
        self.command = command
        self.args = args

        self.shell_id = shell_id
        self.command_id = None

    async def __aenter__(self):
        payload = etree.tostring(
            create_command(self.shell_id, self.command, self.args)
        )

        resp = await _make_winrm_request(self._session, self.host, payload)
        if resp.status != 200:
            await resp.release()
            raise AIOWinRMException(
                "Unhandled http error {}".format(resp.status)
            )

        try:
            data = await resp.text()
            self.command_id = parse_create_command_response(data)
            return self
        finally:
            await resp.release()

    async def __aexit__(self, *a, **kw):
        if self.command_id is None:
            raise RuntimeError("__aexit__ called without __aenter__")

        payload = etree.tostring(cleanup_command(self.shell_id, self.command_id))
        resp = await _make_winrm_request(self._session, self.host, payload)
        await resp.release()

    async def _output_request(self):
        payload = etree.tostring(command_output(self.shell_id, self.command_id))
        resp = await _make_winrm_request(self._session, self.host, payload)
        try:
            if resp.status != 200:
                raise AIOWinRMException(
                    "Unhandled http error {}".format(resp.status)
                )

            data = await resp.text()
            stdout, stderr, return_code, is_done = parse_command_output(data)
            return (
                stdout.decode("utf8"), stderr.decode("utf8"), return_code, is_done
            )
        finally:
            await resp.release()


class WinRmConnection(object):
    """
    Class allows to make multiple winrm requests using the same aio connection
    """

    def __init__(self, session, url):
        self._session = session
        self._url = url
        self._resp = None

    async def request(self, xml_payload):
        str_payload = etree.tostring(xml_payload)
        self._resp = await _make_winrm_request(self._session, self._url, str_payload)
        data = await self._resp.text()
        if self._resp.status == 401:
            raise AIOWinRMException(
                "Unauthorized {}".format(self._resp.status)
            )

        root = etree.fromstring(data)  # raises exception if soap response action is a "fault"
        resp = parse_soap_response(root)
        if self._resp.status != 200:
            # probably superflous because we'll have a soap fault anyway
            raise AIOWinRMException(
                "Unhandled http error {}".format(self._resp.status)
            )
        return resp

    async def close(self):
        if self._resp:
            await self._resp.release()


def _make_winrm_request(session, url, payload):
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'Content-Length': str(len(payload)),
    }
    return session.post(url, data=payload, headers=headers)
