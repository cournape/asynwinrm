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


class AioWinRmRequestClass(aiohttp.ClientRequest):

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