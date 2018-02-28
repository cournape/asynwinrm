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
    parse_create_ps_pipeline_response)


class PowerShellContext(object):

    def __init__(self, session, host):
        self._session = session

        self.host = host
        self.session_id = uuid.uuid4()

        self.std_out = []
        self.std_err = []
        self.exit_code = None

    async def __aenter__(self):
        compat_msg = create_session_capability_message(self.session_id)
        runspace_msg = init_runspace_pool_message(self.session_id)
        creation_payload = Fragmenter.messages_to_fragment_bytes((compat_msg, runspace_msg))

        payload = etree.tostring(create_power_shell_payload(self.session_id, creation_payload))

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

            state = RunspacePoolStateEnum.OPENING
            get_ps_response_payload = etree.tostring(get_ps_response(self.shell_id))
            while state != RunspacePoolStateEnum.OPENED:
                print('requesting')
                keep_ailve_resp = await _make_winrm_request(
                    self._session, self.host, get_ps_response_payload
                )
                data = await keep_ailve_resp.text()
                response_root = parse_soap_response(data)
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
        finally:
            await resp.release()

    async def run_script(self, script):
        script += "\r\nif (!$?) { if($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }"
        command_id = uuid.uuid4()
        message = create_pipeline_message(self.shell_id, command_id, script)
        for fragment in Fragmenter.messages_to_fragments([message]):
            if fragment.start_fragment:
                payload = etree.tostring(create_ps_pipeline(self.shell_id, command_id, fragment.get_bytes()))
                resp = await _make_winrm_request(
                    self._session, self.host, payload
                )
                if resp.status != 200:
                    await resp.release()
                    raise AIOWinRMException(
                        "Unhandled http error {}".format(resp.status)
                    )
                data = await resp.text()
                command_id = parse_create_command_response(data)
            else:
                # TODO
                await _make_winrm_request(
                    self._session, self.host, payload
                )

    async def __aexit__(self, *a, **kw):
        if self.shell_id is None:
            raise RuntimeError("__aexit__ called without __aenter__")

        payload = etree.tostring(close_shell_payload(self.shell_id, power_shell=True))
        resp = await _make_winrm_request(self._session, self.host, payload)
        if resp.status != 200:
            raise Exception('Expected shell to be closed')
        # resp_data = await resp.text()
        await resp.release()


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


"""
class ScriptContext(object):
    def __init__(self, session, host, shell_id, script):
        self._session = session

        self.host = host
        self.script = script

        self.shell_id = shell_id
        self.command_id = None

    async def __aenter__(self):
        payload = etree.tostring(
            create_script(self.shell_id, script)
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
"""


def _make_winrm_request(session, url, payload):
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'Content-Length': str(len(payload)),
    }
    return session.post(url, data=payload, headers=headers)
