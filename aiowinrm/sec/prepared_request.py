import aiohttp


class PreparedRequest(object):

    def __init__(self, url, headers, data, session=None, method=None):
        self.url = url
        self.headers = headers
        self.data = data
        self.session = session
        self.method = method

    def __str__(self):
        return self.url

    async def send(self):
        if not self.session or not self.method:
            raise Exception('Unable to send request without correct session or method')
        fun = getattr(self.session, self.method.lower())
        return await fun(headers=self.headers, data=self.data, url=self.url)


class MyRequestInfo(object):

    def __init__(self, url, method, headers, data=None, session=None):
        self.url = url
        self.method = method
        self.headers = headers
        self.data = data
        self.session = session


class WrappedRequestClass(aiohttp.ClientRequest):

    @property
    def request_info(self):
        body = self.body
        if hasattr(body, '_value'):
            body = body._value
        return MyRequestInfo(self.url,
                             self.method,
                             self.headers,
                             body,
                             self._session)


class WrappedResponseClass(aiohttp.ClientResponse):

    def __init__(self, *args, **kwargs):
        self._peer_cert = None
        self._data = None
        super(WrappedResponseClass, self).__init__(*args, **kwargs)

    @property
    def peer_cert(self):
        return self._peer_cert

    async def start(self, connection, read_until_eof=False):
        try:
            self._peer_cert = connection.transport._ssl_protocol._extra['ssl_object'].getpeercert(True)
        except Exception:
            pass
        return await super(WrappedResponseClass, self).start(connection, read_until_eof)

    def recycle(self):
        req_info = self._request_info
        return PreparedRequest(
            data=req_info.data,
            url=str(self.url),
            headers=req_info.headers,
            method=req_info.method,
            session=req_info.session
        )

    @property
    def ok(self):
        return self.status == 200

    def set_content(self, content):
        self._content = content