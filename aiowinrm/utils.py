import re
import lxml.etree as etree
from aiowinrm.errors import AIOWinRMException


HOST_RE = re.compile("""
(?i)
^((?P<scheme>http[s]?)://)?
(?P<host>[0-9a-z-_.]+)
(:(?P<port>\d+))?
(?P<path>(/)?(wsman)?)?
""", re.VERBOSE)
BOM_CHR = chr(65279)
STRIP_RE = re.compile("xmlns=*[\"\"][^\"\"]*[\"\"]")


# Adapted from pywinrm
def check_url(url, default_to_ssl=True):
    match = HOST_RE.match(url)
    scheme = match.group('scheme')
    port = match.group('port')
    if scheme:
        if not port:
            port = 5986 if scheme == "https" else 5985
    else:
        scheme = 'https' if default_to_ssl else 'https'

    host = match.group('host')
    if not port:
        port = 5986 if default_to_ssl else 5985
    path = match.group('path')
    if not path:
        path = 'wsman'
    return '{0}://{1}:{2}/{3}'.format(scheme, host, port, path.lstrip('/'))


REMOVE_BLANKS_PARSER = etree.XMLParser(remove_blank_text=True)


def xml_remove_spaces(inp):
    root = etree.fromstring(inp, parser=REMOVE_BLANKS_PARSER)
    return etree.tostring(root).decode('utf-8') + '\r\n'


def build_win_rm_url(host, use_https, port=None):
    scheme = 'https' if use_https else 'http'
    if port is None:
        port = 5986 if use_https else 5985
    return f'{scheme}://{host}:{port}/wsman'


def check_for_bom(script):
    if BOM_CHR in script:
        pos = script.index(BOM_CHR)
        raise AIOWinRMException(f'Illegal character found in script at position {pos}')


def _strip_namespace(xml):
    """strips any namespaces from an xml string"""
    try:
        all_matches = STRIP_RE.finditer(xml)
        for match in all_matches:
            xml = xml.replace(match.group(), "")
        return xml
    except Exception as e:
        raise Exception(e)


def _clean_error_msg(msg):
    """converts a Powershell CLIXML message to a more human readable string
    """
    # TODO (pywinrm) prepare unit test, beautify code
    # if the msg does not start with this, return it as is
    if msg.startswith("#< CLIXML\r\n"):
        # for proper xml, we need to remove the CLIXML part
        # (the first line)
        msg_xml = msg[11:]
        try:
            # remove the namespaces from the xml for easier processing
            msg_xml = _strip_namespace(msg_xml)
            root = etree.fromstring(msg_xml)
            # the S node is the error message, find all S nodes
            nodes = root.findall("./S")
            new_msg = ""
            for s in nodes:
                # append error msg string to result, also
                # the hex chars represent CRLF so we replace with newline
                new_msg += s.text.replace("_x000D__x000A_", "\n")
        except Exception as ex:
            # if any of the above fails, the msg was not true xml
            # print a warning and return the orignal string
            # TODO (pywinrm) do not print, raise user defined error instead
            print("Warning: there was a problem converting the Powershell"
                  " error message: %s" % (ex))
        else:
            # if new_msg was populated, that's our error message
            # otherwise the original error message will be used
            if len(new_msg):
                # remove leading and trailing whitespace while we are here
                msg = new_msg.strip()
    return msg
