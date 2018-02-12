import re

from .constants import TranportKind


R_HOST = re.compile("""
(?i)
^((?P<scheme>http[s]?)://)?
(?P<host>[0-9a-z-_.]+)
(:(?P<port>\d+))?
(?P<path>(/)?(wsman)?)?
""", re.VERBOSE)


# Adapted from pywinrm
def parse_host(url, transport):
    match = R_HOST.match(url)
    scheme = match.group('scheme')
    port = match.group('port')
    if scheme and not port:
        port = 5986 if scheme == "https" else 5985

    else:
        if transport == TranportKind.http:
            scheme = "http"
        elif transport == TranportKind.ssl:
            scheme = "https"
        else:
            raise ValueError("Invalid tranport {!r}".format(transport))

    host = match.group('host')
    if not port:
        port = 5986 if transport == TranportKind.ssl else 5985
    path = match.group('path')
    if not path:
        path = 'wsman'
    return '{0}://{1}:{2}/{3}'.format(scheme, host, port, path.lstrip('/'))
