import asyncio
import aiohttp

from aiowinrm.sec import AuthEnum, set_kerb_pwd
from aiowinrm.errors import AIOWinRMException
from aiowinrm.utils import check_url


class ConnectionOptions(object):

    def __init__(self,
                 winrm_url,
                 username,
                 password,
                 auth_method,
                 realm=None,
                 verify_ssl=True,
                 default_to_ssl=True,
                 connector=None,
                 loop=None,
                 allow_plain_text=False,
                 server_certificate_hash=None,
                 ca_trust_path=None,
                 cert_pem=None,
                 cert_key_pem=None,
                 read_timeout_sec=None,
                 kerberos_delegation=False,
                 kerberos_hostname_override=None,
                 message_encryption='auto',
                 credssp_disable_tlsv1_2=False,
                 send_cbt=True,
                 keytab=None,
                 ad_server=None):

        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._connector = connector
        self.url = check_url(winrm_url, default_to_ssl)

        # prevent accidental plain text usage
        if 'https://' not in self.url \
                and not allow_plain_text \
                and auth_method == AuthEnum.Basic:
            raise AIOWinRMException('Usage of HTTP + Basic Auth is insecure and discouraged')

        if isinstance(auth_method, AuthEnum):
            auth_method = auth_method.value
        if auth_method != AuthEnum.Basic.value and not realm:
            raise AIOWinRMException(f'realm is required for {auth_method}')


        # creds
        self.realm = realm
        self.username = username
        self.password = password
        self.ad_server = ad_server

        # sec
        self.verify_ssl = verify_ssl
        self.server_certificate_hash = server_certificate_hash
        self.auth_method = auth_method
        self.ca_trust_path = ca_trust_path
        self.cert_pem = cert_pem
        self.cert_key_pem = cert_key_pem
        self.read_timeout_sec = read_timeout_sec
        self.kerberos_delegation = kerberos_delegation
        self.kerberos_hostname_override = kerberos_hostname_override
        self.message_encryption = message_encryption
        self.credssp_disable_tlsv1_2 = credssp_disable_tlsv1_2
        self.send_cbt = send_cbt
        self.keytab = keytab

    def get_kerb_ticket(self):
        set_kerb_pwd(self.username, self.password, self.realm, self.ad_server)

    @property
    def connector(self):
        if self._connector is None:
            return aiohttp.TCPConnector(loop=self.loop,
                                        verify_ssl=self.verify_ssl,
                                        force_close=False)
