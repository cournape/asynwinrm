import asyncio
from enum import Enum

import aiohttp
import lxml.etree as etree
from aiowinrm.errors import AIOWinRMException
from aiowinrm.soap.protocol import parse_soap_response
from aiowinrm.utils import check_url


class AuthEnum(Enum):

    Basic = 'basic'
    NTLM = 'ntlm'


class ConnectionOptions(object):

    def __init__(self,
                 winrm_url,
                 username,
                 password,
                 domain=None,
                 auth_mode=AuthEnum.Basic,
                 verify_ssl=True,
                 default_to_ssl=True,
                 connector=None,
                 loop=None):
        self.verify_ssl = verify_ssl
        self.loop = asyncio.get_event_loop() \
            if loop is None else loop
        self._connector = connector
        self.url = check_url(winrm_url, default_to_ssl)
        self.domain = domain
        self.username = username
        self.password = password
        self.auth_mode = auth_mode

    @property
    def connector(self):
        if self._connector is None:
            return aiohttp.TCPConnector(loop=self.loop,
                                        verify_ssl=self.verify_ssl)


class NtlmSession(aiohttp.ClientSession):

    def __init__(self,
                 domain,
                 username,
                 password,
                 connector,
                 loop):
        self._domain = domain
        self._username = username
        self._password = password
        super(NtlmSession, self).__init__(connector=connector,
                                          loop=loop)

    def post(self, url, *, data=None, **kwargs):

        super(NtlmSession, self).post(url=url,
                                      data=data,
                                      headers=None,
                                      **kwargs)


class WinRmConnection(object):
    """
    Class allows to make multiple winrm requests using the same aio connection
    """

    def __init__(self, options):
        self.options = options

        self._session = None
        self._resp = None

    @property
    def session(self):
        if self._session is None:
            if self.options.auth_mode == AuthEnum.Basic:
                self._session = self.build_basic_auth_session()
            elif self.options.auth_mode == AuthEnum.NTLM:
                self._session = self.build_ntlm_auth_session()
            else:
                raise Exception('Unknown auth mode')
        return self._session

    def build_ntlm_auth_session(self):
        return NtlmSession(
            domain=self.options.domain,
            username=self.options.username,
            password=self.options.password,
            connector=self.options.connector,
            loop=self.options.loop)

    def build_basic_auth_session(self):
        user = f'{self.options.username}@{self.options.domain}' \
            if self.options.domain else self.options.username
        auth = aiohttp.BasicAuth(user, self.options.password)
        return aiohttp.ClientSession(
            connector=self.options.connector,
            loop=self.options.loop,
            auth=auth)

    async def request(self, xml_payload):
        payload_bytes = etree.tostring(xml_payload)

        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Content-Length': str(len(payload_bytes)),
        }

        self._resp = await self.session.post(self.options.url,
                                             data=payload_bytes,
                                             headers=headers)
        data = await self._resp.text()
        if self._resp.status == 401:
            raise AIOWinRMException(
                "Unauthorized {}".format(self._resp.status)
            )

        root = etree.fromstring(data)

        # raises exception if soap response action is a "fault"
        resp = parse_soap_response(root)
        if self._resp.status != 200:

            # probably superfluous because we'll have a soap fault anyway
            raise AIOWinRMException(
                "Unhandled http error {}".format(self._resp.status)
            )
        return resp

    async def close(self):
        if self._resp:
            await self._resp.release()
        self._session.close()
