import lxml.etree as etree

from aiowinrm.sec.auto_session import AutoSession
from aiowinrm.errors import AIOWinRMException, InvalidCredentialsError
from aiowinrm.soap.protocol import parse_soap_response


class WinRmConnection(object):
    """
    Class allows to make multiple winrm requests using the same aio connection
    """

    def __init__(self, options):
        self.options = options
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self.build_session()

        return self._session

    def build_session(self):
        return AutoSession(
            endpoint=self.options.url,
            realm=self.options.realm,
            username=self.options.username,
            password=self.options.password,
            connector=self.options.connector,
            loop=self.options.loop,
            verify_ssl=self.options.verify_ssl,
            ca_trust_path=self.options.ca_trust_path,
            cert_pem=self.options.cert_pem,
            cert_key_pem=self.options.cert_key_pem,
            read_timeout_sec=self.options.read_timeout_sec,
            kerberos_delegation=self.options.kerberos_delegation,
            kerberos_hostname_override=self.options.kerberos_hostname_override,
            auth_method=self.options.auth_method,
            message_encryption=self.options.message_encryption,
            credssp_disable_tlsv1_2=self.options.credssp_disable_tlsv1_2,
            send_cbt=self.options.send_cbt,
            keytab=self.options.keytab,
        )


    async def request(self, xml_payload):
        payload_bytes = etree.tostring(xml_payload)

        resp = await self.session.winrm_request(self.options.url,
                                                data=payload_bytes)

        if resp.text:
            root = etree.fromstring(resp.text)

            # raises exception if soap response action is a "fault"
            parsed = parse_soap_response(root)
            if resp.status != 200:
                # probably superfluous because we'll have a soap fault anyway
                raise AIOWinRMException(
                    f'Unhandled http error {resp.status}'
                )
            return parsed

        if resp.status != 200:
            raise AIOWinRMException(
                f'Unhandled http error {resp.status}'
            )

        raise RuntimeError('200 code but no data received')

    async def close(self):
        if self._session:
            await self._session.close()
