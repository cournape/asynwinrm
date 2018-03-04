from aiowinrm.shell_context import ShellContext
from aiowinrm.winrm_connection import WinRmConnection

from .soap.protocol import \
    create_command, parse_create_command_response, cleanup_command, \
    command_output, parse_command_output, SoapTimeout


class CommandContext(object):
    def __init__(self,
                 shell_context,
                 command,
                 args=()):
        assert isinstance(shell_context, ShellContext)
        self.command = command
        self.args = args
        self.shell_context = shell_context

        self.command_id = None

    @property
    def _win_rm_connection(self):
        return self.shell_context.win_rm_connection

    @property
    def shell_id(self):
        return self.shell_context.shell_id

    async def __aenter__(self):
        try:
            payload = create_command(self.shell_id,
                                     self.command,
                                     self.args)
            resp = await self._win_rm_connection.request(payload)
            self.command_id = parse_create_command_response(resp)

            return self
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def __aexit__(self, ex=None, *a, **kw):
        if not self._win_rm_connection:
            return

        if self.command_id is None and ex is None:
            raise RuntimeError("__aexit__ called without __aenter__")

        if not isinstance(ex, SoapTimeout):
            payload = cleanup_command(self.shell_id, self.command_id)
            await self._win_rm_connection.request(payload)

    async def output_request(self):
        try:
            payload = command_output(self.shell_id, self.command_id)
            resp = await self._win_rm_connection.request(payload)

            stdout, stderr, return_code, is_done = parse_command_output(resp)
            return (
                stdout.decode("utf8"), stderr.decode("utf8"), return_code, is_done
            )
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

