import aiohttp

from aiowinrm.sec.request import PreparedRequest


class AioWinRmResponseClass(aiohttp.ClientResponse):

    def __init__(self, *args, **kwargs):
        self._peer_cert = None
        self._data = None
        super(AioWinRmResponseClass, self).__init__(*args, **kwargs)

    @property
    def peer_cert(self):
        return self._peer_cert

    async def start(self, connection, read_until_eof=False):
        try:
            self._peer_cert = connection.transport._ssl_protocol._extra['ssl_object'].getpeercert(True)
        except Exception:
            pass
        return await super(AioWinRmResponseClass, self).start(connection, read_until_eof)

    def recycle(self):
        req_info = self._request_info
        return PreparedRequest(
            data=req_info.data,
            url=str(self.url),
            headers=req_info.headers,
            method=req_info.method,
            session=req_info.session
        )

    def set_content(self, content):
        self._content = content