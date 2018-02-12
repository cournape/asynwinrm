import re
from base64 import b64encode

import aiohttp
import asyncio

from aiowinrm.constants import TranportKind
from aiowinrm.utils import parse_host
from .core import CommandContext, ShellContext
import xml.etree.ElementTree as ET


STRIP_RE = re.compile("xmlns=*[\"\"][^\"\"]*[\"\"]")


def _strip_namespace(xml):
    """strips any namespaces from an xml string"""
    try:
        allmatches = STRIP_RE.finditer(xml)
        for match in allmatches:
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
            root = ET.fromstring(msg_xml)
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


async def run_cmd(host,
                  auth,
                  command, args=(),
                  env=None,
                  cwd=None,
                  default_transport=TranportKind.http,
                  verify_ssl=True):
    """
    Run the given command on the given host asynchronously.
    """
    host = parse_host(host, transport=default_transport)
    connector = aiohttp.TCPConnector(loop=asyncio.get_event_loop(),
                                     verify_ssl=verify_ssl)
    async with aiohttp.ClientSession(auth=auth, connector=connector) as session:
        async with ShellContext(session, host, env=env, cwd=cwd) as shell_context:
            async with CommandContext(
                session, host, shell_context.shell_id, command, args
            ) as command_context:
                return_code = None
                stdout_buffer, stderr_buffer = [], []
                is_done = False
                while not is_done:
                    stdout, stderr, return_code, is_done = await command_context._output_request()
                    stdout_buffer.append(stdout)
                    stderr_buffer.append(stderr)
                return ''.join(stdout_buffer), ''.join(stderr_buffer), return_code


async def run_ps(host,
                 auth,
                 script,
                 default_transport=TranportKind.http,
                 verify_ssl=True):
    """
    run PowerShell script

    :param host:
    :param auth:
    :param script:
    :param default_transport:
    :param verify_ssl:
    :return:
    """
    if chr(65279) in script:
        pos = script.index(chr(65279))
        raise Exception('Illegal character found in script at position {}'.format(pos))
    encoded_ps = b64encode(script.encode('utf_16_le')).decode('ascii')
    res = await run_cmd(host=host,
                        auth=auth,
                        command='powershell -encodedcommand {0}'.format(encoded_ps),
                        default_transport=default_transport,
                        verify_ssl=verify_ssl)
    stdout, stderr, return_code = res
    if stderr:
        # if there was an error message, clean it it up and make it human
        # readable
        stderr = _clean_error_msg(stderr)
    return stdout, stderr, return_code



