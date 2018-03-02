from aiowinrm.winrm_connection import WinRmConnection

from .soap.protocol import (
    create_shell_payload, close_shell_payload, parse_create_shell_response,
    create_command, parse_create_command_response, cleanup_command,
    command_output, parse_command_output, SoapTimeout)



class CommandContext(object):
    def __init__(self, session, host, shell_id, command, args=()):
        self._session = session

        self.host = host
        self.command = command
        self.args = args

        self.shell_id = shell_id
        self.command_id = None
        self._win_rm_connection = None

    async def __aenter__(self):
        try:
            payload = create_command(self.shell_id, self.command, self.args)
            self._win_rm_connection = WinRmConnection(self._session, self.host)
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
            await self._win_rm_connection.close()
            raise RuntimeError("__aexit__ called without __aenter__")

        if isinstance(ex, SoapTimeout):
            payload = cleanup_command(self.shell_id, self.command_id)
            await self._win_rm_connection.request(payload)

        await self._win_rm_connection.close()

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

