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

    def __init__(self, url, method, headers, data=None):
        self.url = url
        self.method = method
        self.headers = headers
        self.data = data


class WrappedRequestClass(aiohttp.ClientRequest):

    @property
    def request_info(self):
        return MyRequestInfo(self.url, self.method, self.headers, self.body._value)


class WrappedResponseClass(aiohttp.ClientResponse):

    @property
    def peer_cert(self):
        if hasattr(self, '_peer_cert'):
            return self._peer_cert

    async def start(self, connection, read_until_eof=False):
        try:
            self._peer_cert = connection.transport._ssl_protocol._extra['ssl_object'].getpeercert(True)
        except Exception:
            pass
        return await super(WrappedResponseClass, self).start(connection, read_until_eof)


class ResponseWrapper(object):

    def __init__(self, response, session, request_data, server_cert=None):
        self.request_data = request_data
        self.server_cert = server_cert
        self.response = response
        self.session = session
        self._text = None

    @property
    def status(self):
        return self.response.status

    async def get_text(self, encryption):
        if self._text is None:
            if encryption:
                self.content = await self.response.read()
                self._text = encryption.parse_encrypted_response(self) if self.content else self.content
            else:
                self._text = await self.response.text()
        return self._text

    @property
    def text(self):
        return self._text

    @property
    def headers(self):
        return self.response.headers

    @property
    def url(self):
        return str(self.response.url)

    @property
    def request(self):
        return self.response.request_info

    def recycle(self):
        request = self.request
        return PreparedRequest(
            data=self.request_data,
            url=self.url,
            headers=request.headers,
            method=request.method,
            session=self.session
        )