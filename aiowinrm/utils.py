import re
import lxml.etree as etree

from .constants import TranportKind


R_HOST = re.compile("""
(?i)
^((?P<scheme>http[s]?)://)?
(?P<host>[0-9a-z-_.]+)
(:(?P<port>\d+))?
(?P<path>(/)?(wsman)?)?
""", re.VERBOSE)


# Adapted from pywinrm
# changed transport to default_transport so that it doesn't just change ports
def parse_host(url, default_transport):
    match = R_HOST.match(url)
    scheme = match.group('scheme')
    port = match.group('port')
    if scheme:
        if not port:
            port = 5986 if scheme == "https" else 5985
    else:
        if default_transport == TranportKind.http:
            scheme = "http"
        elif default_transport == TranportKind.ssl:
            scheme = "https"
        else:
            raise ValueError("Invalid tranport {!r}".format(default_transport))

    host = match.group('host')
    if not port:
        port = 5986 if default_transport == TranportKind.ssl else 5985
    path = match.group('path')
    if not path:
        path = 'wsman'
    return '{0}://{1}:{2}/{3}'.format(scheme, host, port, path.lstrip('/'))


REMOVE_BLANKS_PARSER = etree.XMLParser(remove_blank_text=True)


def xml_remove_spaces(inp):
    root = etree.fromstring(inp, parser=REMOVE_BLANKS_PARSER)
    return etree.tostring(root).decode('utf-8') + '\r\n'
