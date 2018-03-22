import os
import inspect
import warnings
import aiohttp

from aiowinrm.sec.encryption import Encryption
from aiowinrm.errors import InvalidCredentialsError, AIOWinRMException
from aiowinrm.sec.request import PreparedRequest, AioWinRmRequestClass
from aiowinrm.sec.response import AioWinRmResponseClass

HAVE_KERBEROS = False
HAVE_CREDSSP = False
HAVE_NTLM = False


try:
    from aiowinrm.sec.kerberos_ import HTTPKerberosAuth, REQUIRED, OPTIONAL, DISABLED
    HAVE_KERBEROS = True
except ImportError:
    pass


try:
    from aiowinrm.sec.ntlm_ import HttpNtlmAuth
    HAVE_NTLM = True
except ImportError as ie:
    pass


"""
NOT IMPLEMENTED (yet?)
please see requests_credssp for implementation

try:
    from aiowinrm.sec.credssp_ import HttpCredSSPAuth

    HAVE_CREDSSP = True
except ImportError as ie:
    pass
"""


class WindowsSession(aiohttp.ClientSession):

    def __init__(self,
                 endpoint,
                 username,
                 password,
                 realm,
                 verify_ssl=True,
                 service='HTTP',
                 ca_trust_path=None,
                 cert_pem=None,
                 cert_key_pem=None,
                 read_timeout_sec=None,
                 kerberos_delegation=False,
                 kerberos_hostname_override=None,
                 auth_method='auto',
                 message_encryption='auto',
                 credssp_disable_tlsv1_2=False,
                 send_cbt=True,
                 keytab=None,
                 connector=None,
                 loop=None):
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.realm = realm
        self.service = service
        self.keytab = keytab
        self.ca_trust_path = ca_trust_path
        self.cert_pem = cert_pem
        self.cert_key_pem = cert_key_pem
        self.read_timeout_sec = read_timeout_sec
        self.verify_ssl = verify_ssl
        self.kerberos_hostname_override = kerberos_hostname_override
        self.message_encryption = message_encryption
        self.credssp_disable_tlsv1_2 = credssp_disable_tlsv1_2
        self.send_cbt = send_cbt
        self._server_cert = None
        self.auth_method = auth_method
        assert isinstance(kerberos_delegation, bool)
        self.kerberos_delegation = kerberos_delegation

        self.default_headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'User-Agent': 'Python AioWinRM client',
            'Connection': 'keep-alive'
        }

        # validate credential requirements for various auth types
        if self.auth_method != 'kerberos':
            if self.auth_method == 'certificate' or (
                            self.auth_method == 'ssl' and (self.cert_pem or self.cert_key_pem)):
                if not self.cert_pem or not self.cert_key_pem:
                    raise InvalidCredentialsError('both cert_pem and cert_key_pem must be specified for cert auth')
                if not os.path.exists(self.cert_pem):
                    raise InvalidCredentialsError('cert_pem file not found (%s)' % self.cert_pem)
                if not os.path.exists(self.cert_key_pem):
                    raise InvalidCredentialsError('cert_key_pem file not found (%s)' % self.cert_key_pem)

            else:
                if not self.username:
                    raise InvalidCredentialsError('auth method %s requires a username' % self.auth_method)
                if self.password is None:
                    raise InvalidCredentialsError('auth method %s requires a password' % self.auth_method)


        # Used for encrypting messages
        self.encryption = None  # The Pywinrm Encryption class used to encrypt/decrypt messages
        if self.message_encryption not in ['auto', 'always', 'never']:
            raise AIOWinRMException(f'invalid message_encryption arg: {self.message_encryption} '
                                    f"Should be 'auto', 'always', or 'never'")

        self.auth = None
        super(WindowsSession, self).__init__(connector=connector,
                                             loop=loop,
                                             response_class=AioWinRmResponseClass,
                                             request_class=AioWinRmRequestClass)

    async def build_auth(self):
        # not using env vars

        encryption_available = False

        if self.auth_method == 'kerberos':
            if not HAVE_KERBEROS:
                raise AIOWinRMException('requested auth method is kerberos, '
                                        'but requests_kerberos is not installed')

            man_args = dict(
                mutual_authentication=REQUIRED,
            )
            opt_args = dict(
                delegate=self.kerberos_delegation,
                force_preemptive=True,
                principal=self.username,
                hostname_override=self.kerberos_hostname_override,
                sanitize_mutual_error_response=False,
                service=self.service,
                send_cbt=self.send_cbt
            )
            kerb_args = self._get_args(man_args, opt_args, HTTPKerberosAuth.__init__)
            self.auth = HTTPKerberosAuth(**kerb_args)
            encryption_available = hasattr(self.auth, 'winrm_encryption_available') \
                                   and self.auth.winrm_encryption_available
        elif self.auth_method in ['certificate', 'ssl']:
            if self.auth_method == 'ssl' and not self.cert_pem and not self.cert_key_pem:
                # 'ssl' was overloaded for HTTPS with optional certificate auth,
                # fall back to basic auth if no cert specified
                user = f'{self.username}@{self.realm}' if self.realm else self.username
                self.auth = aiohttp.BasicAuth(user, self.password)
            else:
                self.cert = (self.cert_pem, self.cert_key_pem)
                self.default_headers['Authorization'] = \
                    'http://schemas.dmtf.org/wbem/wsman/1/wsman/secprofile/https/mutual'
        elif self.auth_method == 'ntlm':
            if not HAVE_NTLM:
                raise AIOWinRMException('requested auth method is ntlm, but ntlm is not installed')
            user = self.username if '\\' in self.username else f'{self.realm}\\{self.username}'
            man_args = dict(
                username=user,
                password=self.password
            )
            opt_args = dict(
                send_cbt=self.send_cbt
            )
            ntlm_args = self._get_args(man_args, opt_args, HttpNtlmAuth.__init__)
            self.auth = HttpNtlmAuth(**ntlm_args)
            # check if requests_ntlm has the session_security attribute available for encryption
            encryption_available = hasattr(self.auth, 'session_security')
        # TODO: ssl is not exactly right here- should really be client_cert
        elif self.auth_method in ['basic', 'plaintext']:
            user = f'{self.username}@{self.realm}' if self.realm else self.username
            self.auth = aiohttp.BasicAuth(user, self.password)
        elif self.auth_method == 'credssp':
            if not HAVE_CREDSSP:
                raise AIOWinRMException('requests auth method is credssp, but requests-credssp is not installed')
            """
            self.auth = HttpCredSSPAuth(username=self.username, password=self.password,
                                               disable_tlsv1_2=self.credssp_disable_tlsv1_2)
            encryption_available = hasattr(self.auth, 'wrap') and hasattr(self.auth, 'unwrap')
            """
        else:
            raise AIOWinRMException('unsupported auth method: %s' % self.auth_method)

        # Will check the current config and see if we need to setup message encryption
        if self.message_encryption == 'always' and not encryption_available:
            raise AIOWinRMException(
                "message encryption is set to 'always' but the selected auth method "
                f'{self.auth_method} does not support it')
        elif encryption_available:
            if self.message_encryption == 'always':
                await self.setup_encryption()
                await self.setup_encryption()
            elif self.message_encryption == 'auto' \
                    and not self.endpoint.lower().startswith('https'):
                await self.setup_encryption()

    async def setup_encryption(self):
        """
        Security context doesn't exist, sending blank message to initialise context
        """

        prepared_request = PreparedRequest(url=self.endpoint,
                                           headers=self.default_headers.copy(),
                                           data=None)
        if callable(self.auth):
            self.auth(prepared_request)
        response = await self._send_prepared_request(prepared_request)
        if hasattr(self.auth, 'handle_response'):
            await self.auth.handle_response(response)
        self.encryption = Encryption(self.auth, self.auth_method)

    async def _send_prepared_request(self, prepared_request):
        """
        After the request has been prepared this will send the request
        and check whether there is some decryption to be done

        :param prepared_request:
        :return:
        """
        assert isinstance(prepared_request, PreparedRequest)
        assert 'Connection' in prepared_request.headers

        # basic auth is handled inside aiohttp rest is handled here
        aio_auth = self.auth if isinstance(self.auth, aiohttp.BasicAuth) else None

        resp = await self.post(url=prepared_request.url,
                               data=prepared_request.data,
                               headers=prepared_request.headers,
                               auth=aio_auth)
        return await self.handle_encryption(resp)

    async def handle_encryption(self, response):
        """
        Handles decrypting the response if encryption is enabled

        :param response:
        :return:
        """
        response_content = await response.read()
        if self.encryption:
            if 'Content-Type' not in response.headers:
                raise Exception('Expected content-type in encrypted response')
            content_type = response.headers['Content-Type']
            decrypted = self.encryption.parse_encrypted_response(
                content_type=content_type,
                response_content=response_content,
                host=response.host)
            response.set_content(decrypted)
        return response

    def _get_args(self, mandatory_args, optional_args, function):
        argspec = set(inspect.getargspec(function).args)
        function_args = dict()
        for name, value in mandatory_args.items():
            if name in argspec:
                function_args[name] = value
            else:
                raise Exception('Function %s does not contain mandatory arg '
                                '%s, check installed version with pip list'
                                % (str(function), name))

        for name, value in optional_args.items():
            if name in argspec:
                function_args[name] = value
            else:
                warnings.warn('Function {function} does not contain optional arg'
                              f' {name}, check installed version with pip list')

        return function_args

    async def winrm_request(self, url, data):
        """
        Sets up auth and runs the request.
        If needed it will also decrypt the message.

        :param url:
        :param data:
        :return:
        """
        if not self.auth:
            await self.build_auth()

        if self.encryption:
            prepared_request = self.encryption.prepare_encrypted_request(self.endpoint, data)
        else:
            prepared_request = PreparedRequest(url, headers=self.default_headers, data=data)

        resp = await self._send_prepared_request(prepared_request)
        if hasattr(self.auth, 'handle_response'):
            resp = await self.auth.handle_response(resp)
        return resp