from aiowinrm.winrm_connection import WinRmConnection

from .soap.protocol import (
    create_shell_payload, close_shell_payload, parse_create_shell_response
)


class ShellContext(object):
    def __init__(self, connection_options, env=None, cwd=None):
        self.env = env
        self.cwd = cwd

        self.shell_id = None
        self._connection_options = connection_options
        self._win_rm_connection = None

    async def __aenter__(self):
        try:
            payload = create_shell_payload(self.env, self.cwd)
            self._win_rm_connection = WinRmConnection(self._connection_options)
            resp = await self._win_rm_connection.request(payload)
            self.shell_id = parse_create_shell_response(resp)
            return self
        except Exception as ex:
            await self.__aexit__(ex=ex)
            raise

    async def __aexit__(self, ex=None, *a, **kw):
        if not self._win_rm_connection:
            return

        if self.shell_id is None and ex is None:
            raise RuntimeError("__aexit__ called without __aenter__")

        if self.shell_id:
            payload = close_shell_payload(self.shell_id)
            await self._win_rm_connection.request(payload)
        await self._win_rm_connection.close()

    @property
    def win_rm_connection(self):
        return self._win_rm_connection
