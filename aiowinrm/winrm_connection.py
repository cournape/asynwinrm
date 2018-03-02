import lxml.etree as etree
from aiowinrm.errors import AIOWinRMException
from aiowinrm.soap.protocol import parse_soap_response


class WinRmConnection(object):
    """
    Class allows to make multiple winrm requests using the same aio connection
    """

    def __init__(self, session, url):
        self._session = session
        self._url = url
        self._resp = None

    async def request(self, xml_payload):
        payload_bytes = etree.tostring(xml_payload)

        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Content-Length': str(len(payload_bytes)),
        }
        self._resp = await self._session.post(self._url,
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
