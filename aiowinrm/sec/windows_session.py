from __future__ import unicode_literals

import ssl
import sys
import os
import inspect

import aiohttp

from aiowinrm.case_insensitive_dict import CaseInsensitiveDict
from aiowinrm.sec.encryption import Encryption
from aiowinrm.errors import InvalidCredentialsError, AIOWinRMException, AIOWinRMTransportError
from aiowinrm.sec.prepared_request import PreparedRequest, WrappedResponseClass, WrappedRequestClass

is_py2 = sys.version[0] == '2'

if is_py2:
    # use six for this instead?
    unicode_type = type(u'')
else:
    # use six for this instead?
    unicode_type = type(u'')

import warnings
from distutils.util import strtobool

HAVE_KERBEROS = False
HAVE_CREDSSP = False
HAVE_NTLM = False

try:
    from aiowinrm.sec.kerberos_ import HTTPKerberosAuth, REQUIRED, OPTIONAL, DISABLED
    HAVE_KERBEROS = True
except ImportError:
    pass

"""
try:
    from requests_ntlm import HttpNtlmAuth

    HAVE_NTLM = True
except ImportError as ie:
    pass


try:
    from requests_credssp import HttpCredSSPAuth

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
                 service='HTTP',  # not touched
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

        # defensively parse this to a bool
        if isinstance(kerberos_delegation, bool):
            self.kerberos_delegation = kerberos_delegation
        else:
            self.kerberos_delegation = bool(strtobool(str(kerberos_delegation)))

        self.auth_method = auth_method
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
                    raise InvalidCredentialsError("both cert_pem and cert_key_pem must be specified for cert auth")
                if not os.path.exists(self.cert_pem):
                    raise InvalidCredentialsError("cert_pem file not found (%s)" % self.cert_pem)
                if not os.path.exists(self.cert_key_pem):
                    raise InvalidCredentialsError("cert_key_pem file not found (%s)" % self.cert_key_pem)

            else:
                if not self.username:
                    raise InvalidCredentialsError("auth method %s requires a username" % self.auth_method)
                if self.password is None:
                    raise InvalidCredentialsError("auth method %s requires a password" % self.auth_method)


        # Used for encrypting messages
        self.encryption = None  # The Pywinrm Encryption class used to encrypt/decrypt messages
        if self.message_encryption not in ['auto', 'always', 'never']:
            raise AIOWinRMException(
                "invalid message_encryption arg: %s. Should be 'auto', 'always', or 'never'" % self.message_encryption)

        self.auth = None
        self.headers = CaseInsensitiveDict()
        super(WindowsSession, self).__init__(connector=connector,
                                             loop=loop,
                                             response_class=WrappedResponseClass,
                                             request_class=WrappedRequestClass)

    async def build_auth(self):
        # not using env vars

        encryption_available = False

        if self.auth_method == 'kerberos':
            if not HAVE_KERBEROS:
                raise AIOWinRMException("requested auth method is kerberos, but requests_kerberos is not installed")

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
            encryption_available = hasattr(self.auth, 'winrm_encryption_available') and self.auth.winrm_encryption_available
        elif self.auth_method in ['certificate', 'ssl']:
            if self.auth_method == 'ssl' and not self.cert_pem and not self.cert_key_pem:
                # 'ssl' was overloaded for HTTPS with optional certificate auth,
                # fall back to basic auth if no cert specified
                user = f'{self.username}@{self.realm}' if self.realm else self.username
                self.auth = aiohttp.BasicAuth(user, self.password)
            else:
                self.cert = (self.cert_pem, self.cert_key_pem)
                self.headers['Authorization'] = \
                    "http://schemas.dmtf.org/wbem/wsman/1/wsman/secprofile/https/mutual"
        elif self.auth_method == 'ntlm':
            if not HAVE_NTLM:
                raise AIOWinRMException("requested auth method is ntlm, but requests_ntlm is not installed")
            """
            man_args = dict(
                username=self.username,
                password=self.password
            )
            opt_args = dict(
                send_cbt=self.send_cbt
            )
            ntlm_args = self._get_args(man_args, opt_args, HttpNtlmAuth.__init__)
            self.auth = HttpNtlmAuth(**ntlm_args)
            # check if requests_ntlm has the session_security attribute available for encryption
            encryption_available = hasattr(self.auth, 'session_security')
            """
        # TODO: ssl is not exactly right here- should really be client_cert
        elif self.auth_method in ['basic', 'plaintext']:
            user = f'{self.username}@{self.realm}' if self.realm else self.username
            self.auth = aiohttp.BasicAuth(user, self.password)
        elif self.auth_method == 'credssp':
            if not HAVE_CREDSSP:
                raise AIOWinRMException("requests auth method is credssp, but requests-credssp is not installed")
            """
            self.auth = HttpCredSSPAuth(username=self.username, password=self.password,
                                               disable_tlsv1_2=self.credssp_disable_tlsv1_2)
            encryption_available = hasattr(self.auth, 'wrap') and hasattr(self.auth, 'unwrap')
            """
        else:
            raise AIOWinRMException("unsupported auth method: %s" % self.auth_method)

        self.headers.update(self.default_headers)

        # Will check the current config and see if we need to setup message encryption
        if self.message_encryption == 'always' and not encryption_available:
            raise AIOWinRMException(
                "message encryption is set to 'always' but the selected auth method %s does not support it" % self.auth_method)
        elif encryption_available:
            if self.message_encryption == 'always':
                await self.setup_encryption()
            elif self.message_encryption == 'auto' and not self.endpoint.lower().startswith('https'):
                await self.setup_encryption()

    async def setup_encryption(self):
        # Security context doesn't exist, sending blank message to initialise context
        prepared_request = PreparedRequest(self.endpoint, headers=self.default_headers.copy(), data=None)
        if callable(self.auth):
            self.auth(prepared_request)
        response = await self._send_message_request(prepared_request)
        if hasattr(self.auth, 'handle_response'):
            await self.auth.handle_response(response)
        self.encryption = Encryption(self.auth, self.auth_method)

    async def _send_message_request(self, prepared_request):
        # handle other codes in application
        assert isinstance(prepared_request, PreparedRequest)
        if 'Connection' not in prepared_request.headers:
            print('Here')
        resp = await self.post(url=prepared_request.url,
                               data=prepared_request.data,
                               headers=prepared_request.headers)
        return await self.handle_encryption(resp)

    async def handle_encryption(self, response):
        await response.read()
        if self.encryption:
            await self.encryption.parse_encrypted_response(response)
        return response

    def _get_args(self, mandatory_args, optional_args, function):
        argspec = set(inspect.getargspec(function).args)
        function_args = dict()
        for name, value in mandatory_args.items():
            if name in argspec:
                function_args[name] = value
            else:
                raise Exception("Function %s does not contain mandatory arg "
                                "%s, check installed version with pip list"
                                % (str(function), name))

        for name, value in optional_args.items():
            if name in argspec:
                function_args[name] = value
            else:
                warnings.warn("Function %s does not contain optional arg %s, "
                              "check installed version with pip list"
                              % (str(function), name))

        return function_args

    async def winrm_request(self, url, data=None):

        if not self.auth:
            await self.build_auth()

        if self.encryption:
            prepared_request = self.encryption.prepare_encrypted_request(self.endpoint, data)
        else:
            # request = requests.Request('POST', self.endpoint, data=data)
            # prepared_request = self.session.prepare_request(request)
            prepared_request = PreparedRequest(url, headers=self.default_headers, data=data)

        resp = await self._send_message_request(prepared_request)
        resp = await self.handle_encryption(resp)
        if hasattr(self.auth, 'handle_response'):
            resp = await self.auth.handle_response(resp)
        return resp