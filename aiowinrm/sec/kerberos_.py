from urllib.parse import urlparse

from aiowinrm.sec.utils import get_certificate_hash

try:
    import kerberos
except ImportError:
    import winkerberos as kerberos
import logging
import re


class MutualAuthenticationError(Exception):
    """
    Mutual Authentication Error
    """


class KerberosExchangeError(Exception):
    """
    Kerberos Exchange Failed Error
    """


log = logging.getLogger(__name__)


"""
Different types of mutual authentication:
 with mutual_authentication set to REQUIRED, all responses will be
  authenticated with the exception of errors. Errors will have their contents
  and headers stripped. If a non-error response cannot be authenticated, a
  MutualAuthenticationError exception will be raised.
with mutual_authentication set to OPTIONAL, mutual authentication will be
  attempted if supported, and if supported and failed, a
  MutualAuthenticationError exception will be raised. Responses which do not
  support mutual authentication will be returned directly to the user.
with mutual_authentication set to DISABLED, mutual authentication will not be
  attempted, even if supported.
"""


REQUIRED = 1
OPTIONAL = 2
DISABLED = 3


class NoCertificateRetrievedWarning(Warning):
    pass


def _negotiate_value(response):
    """
    Extracts the gssapi authentication token from the appropriate header
    """
    if hasattr(_negotiate_value, 'regex'):
        regex = _negotiate_value.regex
    else:
        # There's no need to re-compile this EVERY time it is called. Compile
        # it once and you won't have the performance hit of the compilation.
        regex = re.compile('(?:.*,)*\s*Negotiate\s*([^,]*),?', re.I)
        _negotiate_value.regex = regex

    authreq = response.headers.get('www-authenticate', None)

    if authreq:
        match_obj = regex.search(authreq)
        if match_obj:
            return match_obj.group(1)

    return None


def _get_channel_bindings_application_data(response):
    """
    https://tools.ietf.org/html/rfc5929 4. The 'tls-server-end-point' Channel Binding Type

    Gets the application_data value for the 'tls-server-end-point' CBT Type.
    This is ultimately the SHA256 hash of the certificate of the HTTPS endpoint
    appended onto tls-server-end-point. This value is then passed along to the
    kerberos library to bind to the auth response. If the socket is not an SSL
    socket or the raw HTTP object is not a urllib3 HTTPResponse then None will
    be returned and the Kerberos auth will use GSS_C_NO_CHANNEL_BINDINGS

    :param response: The original 401 response from the server
    :return: byte string used on the application_data.value field on the CBT struct
    """

    application_data = None
    if response.peer_cert is not None:
        certificate_hash = get_certificate_hash(response.peer_cert)
        application_data = b'tls-server-end-point:' + certificate_hash
    return application_data


class HTTPKerberosAuth(object):
    """
    Attaches HTTP GSSAPI/Kerberos Authentication to the given Request object.
    """

    def __init__(
            self, mutual_authentication=REQUIRED,
            service='HTTP', delegate=False, force_preemptive=False,
            principal=None, hostname_override=None,
            sanitize_mutual_error_response=True, send_cbt=True):
        self.context = {}
        self.mutual_authentication = mutual_authentication
        self.delegate = delegate
        self.pos = None
        self.service = service
        self.force_preemptive = force_preemptive
        self.principal = principal
        self.hostname_override = hostname_override
        self.sanitize_mutual_error_response = sanitize_mutual_error_response
        self.auth_done = False
        self.winrm_encryption_available = hasattr(kerberos, 'authGSSWinRMEncryptMessage')

        # Set the CBT values populated after the first response
        self.send_cbt = send_cbt
        self.cbt_binding_tried = False
        self.cbt_struct = None

    def generate_request_header(self, response, host, is_preemptive=False):
        """
        Generates the GSSAPI authentication token with kerberos.

        If any GSSAPI step fails, raise KerberosExchangeError
        with failure detail.
        """

        # Flags used by kerberos module.
        gssflags = kerberos.GSS_C_MUTUAL_FLAG | kerberos.GSS_C_SEQUENCE_FLAG
        if self.delegate:
            gssflags |= kerberos.GSS_C_DELEG_FLAG

        kerb_stage = 'authGSSClientInit()'
        try:
            # contexts still need to be stored by host, but hostname_override
            # allows use of an arbitrary hostname for the kerberos exchange
            # (eg, in cases of aliased hosts, internal vs external, CNAMEs
            # w/ name-based HTTP hosting)
            kerb_host = self.hostname_override if self.hostname_override is not None else host
            kerb_spn = '{0}@{1}'.format(self.service, kerb_host)

            result, self.context[host] = kerberos.authGSSClientInit(kerb_spn,
                gssflags=gssflags, principal=self.principal)

            if result < 1:
                raise EnvironmentError(result, kerb_stage)

            # if we have a previous response from the server, use it to continue
            # the auth process, otherwise use an empty value
            negotiate_resp_value = '' if is_preemptive else _negotiate_value(response)

            kerb_stage = 'authGSSClientStep()'
            # If this is set pass along the struct to Kerberos
            if self.cbt_struct:
                result = kerberos.authGSSClientStep(self.context[host],
                                                    negotiate_resp_value,
                                                    channel_bindings=self.cbt_struct)
            else:
                result = kerberos.authGSSClientStep(self.context[host],
                                                    negotiate_resp_value)

            if result < 0:
                raise EnvironmentError(result, kerb_stage)

            kerb_stage = 'authGSSClientResponse()'
            gss_response = kerberos.authGSSClientResponse(self.context[host])

            return 'Negotiate {0}'.format(gss_response)

        except kerberos.GSSError as error:
            log.exception(
                'generate_request_header(): {0} failed:'.format(kerb_stage))
            log.exception(error)
            raise KerberosExchangeError('%s failed: %s' % (kerb_stage, str(error.args)))

        except EnvironmentError as error:
            # ensure we raised this for translation to KerberosExchangeError
            # by comparing errno to result, re-raise if not
            if error.errno != result:
                raise
            message = '{0} failed, result: {1}'.format(kerb_stage, result)
            log.error('generate_request_header(): {0}'.format(message))
            raise KerberosExchangeError(message)

    async def authenticate_user(self, response, **kwargs):
        """
        Handles user authentication with gssapi/kerberos
        """

        try:
            auth_header = self.generate_request_header(response, response.host)
        except KerberosExchangeError:
            # GSS Failure, return existing response
            return response

        log.debug('authenticate_user(): Authorization header: {0}'.format(
            auth_header))

        prepared_request = response.recycle()
        prepared_request.headers['Authorization'] = auth_header
        _r = await prepared_request.send()

        log.debug('authenticate_user(): returning {0}'.format(_r))
        return _r

    async def handle_401(self, response, **kwargs):
        """
        Handles 401's, attempts to use gssapi/kerberos authentication
        """

        log.debug('handle_401(): Handling: 401')
        if _negotiate_value(response) is not None:
            _r = await self.authenticate_user(response, **kwargs)
            log.debug('handle_401(): returning {0}'.format(_r))
            return _r
        else:
            log.debug('handle_401(): Kerberos is not supported')
            log.debug('handle_401(): returning {0}'.format(response))
            return response

    def handle_other(self, response):
        """
        Handles all responses with the exception of 401s.

        This is necessary so that we can authenticate responses if requested
        """

        log.debug('handle_other(): Handling: %d' % response.status)

        if self.mutual_authentication in (REQUIRED, OPTIONAL) and not self.auth_done:

            is_http_error = response.status >= 400

            if _negotiate_value(response) is not None:
                log.debug('handle_other(): Authenticating the server')
                if not self.authenticate_server(response):
                    # Mutual authentication failure when mutual auth is wanted,
                    # raise an exception so the user doesn't use an untrusted
                    # response.
                    log.error('handle_other(): Mutual authentication failed')
                    raise MutualAuthenticationError('Unable to authenticate '
                                                    '{0}'.format(response))

                # Authentication successful
                log.debug('handle_other(): returning {0}'.format(response))
                self.auth_done = True
                return response

            elif is_http_error or self.mutual_authentication == OPTIONAL:
                if not response.ok:
                    log.error('handle_other(): Mutual authentication unavailable '
                              'on {0} response'.format(response.status))

                if(self.mutual_authentication == REQUIRED and
                       self.sanitize_mutual_error_response):
                    return response
                else:
                    return response
            else:
                # Unable to attempt mutual authentication when mutual auth is
                # required, raise an exception so the user doesn't use an
                # untrusted response.
                log.error('handle_other(): Mutual authentication failed')
                raise MutualAuthenticationError('Unable to authenticate '
                                                '{0}'.format(response))
        else:
            log.debug('handle_other(): returning {0}'.format(response))
            return response

    def authenticate_server(self, response):
        """
        Uses GSSAPI to authenticate the server.

        Returns True on success, False on failure.
        """

        log.debug('authenticate_server(): Authenticate header: {0}'.format(
            _negotiate_value(response)))

        host = response.host

        try:
            # If this is set pass along the struct to Kerberos
            if self.cbt_struct:
                result = kerberos.authGSSClientStep(self.context[host],
                                                    _negotiate_value(response),
                                                    channel_bindings=self.cbt_struct)
            else:
                result = kerberos.authGSSClientStep(self.context[host],
                                                    _negotiate_value(response))
        except kerberos.GSSError:
            log.exception('authenticate_server(): authGSSClientStep() failed:')
            return False

        if result < 1:
            log.error('authenticate_server(): authGSSClientStep() failed: '
                      '{0}'.format(result))
            return False

        log.debug('authenticate_server(): returning {0}'.format(response))
        return True

    async def handle_response(self, response, **kwargs):
        """
        Takes the given response and tries kerberos-auth, as needed.
        """
        num_401s = kwargs.pop('num_401s', 0)

        # Check if we have already tried to get the CBT data value
        if not self.cbt_binding_tried and self.send_cbt:
            # If we haven't tried, try getting it now
            cbt_application_data = _get_channel_bindings_application_data(response)
            if cbt_application_data:
                # Only the latest version of pykerberos has this method available
                try:
                    self.cbt_struct = kerberos.channelBindings(application_data=cbt_application_data)
                except AttributeError:
                    # Using older version set to None
                    self.cbt_struct = None
            # Regardless of the result, set tried to True so we don't waste time next time
            self.cbt_binding_tried = True

        if response.status == 401 and num_401s < 2:
            # 401 Unauthorized. Handle it, and if it still comes back as 401,
            # that means authentication failed.
            _r = await self.handle_401(response, **kwargs)
            log.debug('handle_response(): returning %s', _r)
            log.debug('handle_response() has seen %d 401 responses', num_401s)
            num_401s += 1
            return await self.handle_response(_r, num_401s=num_401s, **kwargs)
        elif response.status == 401 and num_401s >= 2:
            # Still receiving 401 responses after attempting to handle them.
            # Authentication has failed. Return the 401 response.
            log.debug('handle_response(): returning 401 %s', response)
            return response
        else:
            _r = self.handle_other(response)
            log.debug('handle_response(): returning %s', _r)
            return _r

    def wrap_winrm(self, host, message):
        if not self.winrm_encryption_available:
            raise NotImplementedError('WinRM encryption is not available on the installed version of pykerberos')

        return kerberos.authGSSWinRMEncryptMessage(self.context[host], message)

    def unwrap_winrm(self, host, message, header):
        if not self.winrm_encryption_available:
            raise NotImplementedError('WinRM encryption is not available on the installed version of pykerberos')

        return kerberos.authGSSWinRMDecryptMessage(self.context[host], message, header)

    def __call__(self, request):
        if self.force_preemptive and not self.auth_done:
            # add Authorization header before we receive a 401
            # by the 401 handler
            host = urlparse(request.url).hostname

            auth_header = self.generate_request_header(None, host, is_preemptive=True)

            log.debug('HTTPKerberosAuth: Preemptive Authorization header: {0}'.format(auth_header))

            request.headers['Authorization'] = auth_header
            request.headers['Connection'] = 'keep-alive'

        return request
