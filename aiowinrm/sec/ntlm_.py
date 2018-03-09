import binascii
from aiowinrm.sec.response import AioWinRmResponseClass
from aiowinrm.sec.utils import get_certificate_hash
from ntlm_auth import ntlm


class HttpNtlmAuth(object):
    """
    HTTP NTLM Authentication Handler for Requests.

    Supports pass-the-hash.
    """

    def __init__(self, username, password, send_cbt=True):
        """Create an authentication handler for NTLM over HTTP.

        :param str username: Username in 'domain\\username' format
        :param str password: Password
        :param bool send_cbt: Will send the channel bindings over a HTTPS channel (Default: True)
        """
        if ntlm is None:
            raise Exception('NTLM libraries unavailable')

        # parse the username
        try:
            self.domain, self.username = username.split('\\', 1)
        except ValueError:
            self.username = username
            self.domain = ''

        if self.domain:
            self.domain = self.domain.upper()
        self.password = password
        self.send_cbt = send_cbt

        # This exposes the encrypt/decrypt methods used to encrypt and decrypt messages
        # sent after ntlm authentication. These methods are utilised by libraries that
        # call requests_ntlm to encrypt and decrypt the messages sent after authentication
        self.session_security = None

    async def retry_using_http_NTLM_auth(self, auth_header_field, auth_header,
                                         response, auth_type, args):
        """
        Attempt to authenticate using HTTP NTLM challenge/response.
        """
        assert isinstance(response, AioWinRmResponseClass)
        # Get the certificate of the server if using HTTPS for CBT
        server_certificate_hash = self._get_server_cert(response)

        if auth_header in response.request_info.headers:
            return response

        request = response.recycle()

        # ntlm returns the headers as a base64 encoded bytestring. Convert to
        # a string.
        context = ntlm.Ntlm()
        negotiate_message = context.create_negotiate_message(self.domain).decode('ascii')
        request.headers[auth_header] = f'{auth_type} {negotiate_message}'

        # NOTE: A streaming response breaks authentication.
        # is this something iohttp does?

        response2 = await request.send()
        request = response2.recycle()

        # this is important for some web applications that store
        # authentication-related info in cookies (it took a long time to
        # figure out)
        if response2.headers.get('set-cookie'):
            request.headers['Cookie'] = response2.headers.get('set-cookie')

        # get the challenge
        auth_header_value = response2.headers[auth_header_field]

        auth_strip = auth_type + ' '

        ntlm_header_value = next(
            s for s in (val.lstrip() for val in auth_header_value.split(','))
            if s.startswith(auth_strip)
        ).strip()

        # Parse the challenge in the ntlm context
        context.parse_challenge_message(ntlm_header_value[len(auth_strip):])

        # build response
        # Get the response based on the challenge message
        authenticate_message = context.create_authenticate_message(
            self.username,
            self.password,
            self.domain,
            server_certificate_hash=server_certificate_hash
        )
        authenticate_message = authenticate_message.decode('ascii')
        request.headers[auth_header] = f'{auth_type} {authenticate_message}'

        response3 = await request.send()

        # Get the session_security object created by ntlm-auth for signing and sealing of messages
        self.session_security = context.session_security

        return response3

    async def handle_response(self, response, **kwargs):
        """
        The actual hook handler.
        """
        if response.status == 401:
            # Handle server auth.
            www_authenticate = response.headers.get('www-authenticate', '').lower()
            auth_type = _auth_type_from_header(www_authenticate)

            if auth_type is not None:
                return await self.retry_using_http_NTLM_auth(
                    'www-authenticate',
                    'Authorization',
                    response,
                    auth_type,
                    kwargs
                )
        elif response.status == 407:
            # If we didn't have server auth, do proxy auth.
            proxy_authenticate = response.headers.get(
                'proxy-authenticate', ''
            ).lower()
            auth_type = _auth_type_from_header(proxy_authenticate)
            if auth_type is not None:
                return await self.retry_using_http_NTLM_auth(
                    'proxy-authenticate',
                    'Proxy-authorization',
                    response,
                    auth_type,
                    kwargs
                )

        return response

    def _get_server_cert(self, response):
        """
        The certificate hash is then used with NTLMv2 authentication for
        Channel Binding Tokens support. If the raw object is not a urllib3 HTTPReponse (default with requests)
        then no certificate will be returned.

        :param response: The original 401 response from the server
        :return: The hash of the DER encoded certificate at the request_url or None if not a HTTPS endpoint
        """
        assert isinstance(response, AioWinRmResponseClass)
        if self.send_cbt and response.peer_cert:
            certificate_hash_bytes = get_certificate_hash(response.peer_cert)
            return binascii.hexlify(certificate_hash_bytes).decode().upper()
        else:
            return None

    def __call__(self, request):
        # we must keep the connection because NTLM authenticates the
        # connection, not single requests
        request.headers['Connection'] = 'Keep-Alive'

        return request


def _auth_type_from_header(header):
    """
    Given a WWW-Authenticate or Proxy-Authenticate header, returns the
    authentication type to use. We prefer NTLM over Negotiate if the server
    suppports it.
    """
    if 'ntlm' in header:
        return 'NTLM'
    elif 'negotiate' in header:
        return 'Negotiate'

    return None
