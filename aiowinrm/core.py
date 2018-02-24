import uuid

import lxml.etree as etree

from aiowinrm.psrp.fragmenter import Fragmenter
from aiowinrm.psrp.messages import create_session_capability_message, init_runspace_pool_message
from aiowinrm.psrp.runspacepool_state import RunspacePoolState
from .errors import AIOWinRMException
from .soap.protocol import (
    create_shell_payload, close_shell_payload, parse_create_shell_response,
    create_command, parse_create_command_response, cleanup_command,
    command_output, parse_command_output,
    create_power_shell_payload, keepalive_msg, parse_soap_response)


class PowerShellContext(object):

    def __init__(self, session, host, script):
        self._session = session
        self.script = script

        self.host = host
        self.session_id = uuid.uuid4()

    async def __aenter__(self):
        a = 1
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

            state = RunspacePoolState.OPENING
            keep_alive_payload = etree.tostring(keepalive_msg(self.shell_id))
            while state != RunspacePoolState.OPENED:
                keep_ailve_resp = await _make_winrm_request(
                    self._session, self.host, keep_alive_payload
                )
                data = await keep_ailve_resp.text()
                response_root = parse_soap_response(data)

            return self
        finally:
            await resp.release()

    async def __aexit__(self, *a, **kw):
        if self.shell_id is None:
            raise RuntimeError("__aexit__ called without __aenter__")

        payload = etree.tostring(close_shell_payload(self.shell_id))
        resp = await _make_winrm_request(self._session, self.host, payload)
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
