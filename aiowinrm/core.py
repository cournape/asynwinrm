import lxml.etree as etree

from .constants import TranportKind
from .errors import AIOWinRMException
from .soap.protocol import (
    create_shell_payload, close_shell_payload, parse_create_shell_response,
    create_command, parse_create_command_response, cleanup_command,
    command_output, parse_command_output
)
from .utils import parse_host


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


def _make_winrm_request(session, url, payload):
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'Content-Length': str(len(payload)),
    }

    return session.post(url, data=payload, headers=headers)
