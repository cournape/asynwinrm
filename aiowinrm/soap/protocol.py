import base64

import six

import lxml.etree as etree

from aiowinrm.psrp.defragmenter import MessageDefragmenter
from .header import Header
from .namespaces import NAMESPACE, SOAP_ENV, WIN_SHELL, ADDRESSING


class SoapException(Exception):
    pass


class WsManException(Exception):
    pass


def _wrap_envelope(header, body):
    envelope = etree.Element(SOAP_ENV + "Envelope", nsmap=NAMESPACE)
    envelope.append(header.to_dom())
    envelope.append(body)
    return envelope


def _first_node_text(root, ns, tag):
    lst = root.findall('.//' + ns + tag)
    if lst:
        return lst[0].text


def create_shell_payload(env=None, cwd=None):
    """ Create the XML payload to create a new shell.

    Parameters
    ----------
    env : dict or None
        Key/value pairs for the running environment
    cwd : str or None
        Current directory in the created shell

    Returns
    -------
    envelope : etree.Element
        lxml node for the whole envelope
    """
    header = Header(
        action="http://schemas.xmlsoap.org/ws/2004/09/transfer/Create",
        options={"WINRS_NOPROFILE": "FALSE", "WINRS_CODEPAGE": "65001"},
    )

    body = etree.Element(SOAP_ENV + "Body")
    shell = etree.SubElement(body, WIN_SHELL + "Shell")
    output_streams = etree.SubElement(shell, WIN_SHELL + "OutputStreams")
    output_streams.text = "stdout stderr"
    input_streams = etree.SubElement(shell, WIN_SHELL + "InputStreams")
    input_streams.text = "stdin"

    if env is not None:
        environment = etree.SubElement(shell, WIN_SHELL + "Environment")
        for key, value in env.items():
            variable = etree.SubElement(
                environment, WIN_SHELL + "Variable", Name=key
            )
            variable.text = value

    if cwd is not None:
        working_directory = etree.SubElement(
            shell, WIN_SHELL + "WorkingDirectory"
        )
        working_directory.text = cwd

    return _wrap_envelope(header, body)


def create_power_shell_payload(session_id, creation_payload):
    session_id = str(session_id).upper()
    header = Header(
        action="http://schemas.xmlsoap.org/ws/2004/09/transfer/Create",
        session_id="",
        options={"protocolversion": "2.3"},
        resource_uri="http://schemas.microsoft.com/powershell/Microsoft.PowerShell",
        timeout="PT60S"
    )
    body = etree.Element(SOAP_ENV + "Body")
    shell = etree.SubElement(body, WIN_SHELL + "Shell")
    shell.attrib['ShellId'] = session_id
    output_streams = etree.SubElement(shell, WIN_SHELL + "OutputStreams")
    output_streams.text = "stdout stderr"
    input_streams = etree.SubElement(shell, WIN_SHELL + "InputStreams")
    input_streams.text = "stdin pr"

    assert isinstance(creation_payload, bytes)
    creation_xml = etree.SubElement(shell, "creationXml")
    creation_xml.text = base64.b64encode(creation_payload)
    creation_xml.set('xmlns', 'http://schemas.microsoft.com/powershell')

    return _wrap_envelope(header, body)


def create_ps_pipeline(shell_id, pipeline_id, creation_payload):
    assert isinstance(creation_payload, bytes)
    shell_id = str(shell_id).upper()
    pipeline_id = str(pipeline_id).upper()
    header = Header(
        action='http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Command',
        shell_id=shell_id,
        resource_uri="http://schemas.microsoft.com/powershell/Microsoft.PowerShell",
        timeout="PT60S"
    )
    body = etree.Element(SOAP_ENV + "Body")
    commandline = etree.SubElement(body, WIN_SHELL + "CommandLine")
    commandline.attrib['CommandId'] = pipeline_id
    command = etree.SubElement(commandline, WIN_SHELL + "Command")
    command.text = "Invoke-Expression"
    arguments = etree.SubElement(commandline, WIN_SHELL + "Arguments")
    arguments.text = base64.b64encode(creation_payload)

    return _wrap_envelope(header, body)


def create_send_payload(shell_id, command_id, send_payload):
    assert isinstance(send_payload, bytes)
    shell_id = str(shell_id).upper()
    header = Header(
        action='http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Send',
        shell_id=shell_id,
        resource_uri="http://schemas.microsoft.com/powershell/Microsoft.PowerShell",
        timeout="PT60S"
    )
    body = etree.Element(SOAP_ENV + "Body")
    send = etree.SubElement(body, WIN_SHELL + "Send")
    stream = etree.SubElement(send, WIN_SHELL + "Stream")
    stream.text = base64.b64encode(send_payload)
    stream.attrib['Name'] = 'stdin'
    stream.attrib['CommandId'] = command_id

    return _wrap_envelope(header, body)


def get_ps_response(shell_id):
    """

    :param shell_id:
    :return:
    """
    header = Header(
        action="http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Receive",
        shell_id=shell_id,
        options={
            "WSMAN_CMDSHELL_OPTION_KEEPALIVE": "TRUE"
        },
        resource_uri="http://schemas.microsoft.com/powershell/Microsoft.PowerShell"
    )
    body = etree.Element(SOAP_ENV + "Body")
    receive = etree.SubElement(body, WIN_SHELL + "Receive")
    desired_stream = etree.SubElement(receive, WIN_SHELL + "DesiredStream")
    desired_stream.text = "stdout"

    return _wrap_envelope(header, body)


def close_shell_payload(shell_id, power_shell=False):
    header = Header(
        action="http://schemas.xmlsoap.org/ws/2004/09/transfer/Delete",
        shell_id=shell_id,
    )
    if power_shell:
        header.resource_uri = "http://schemas.microsoft.com/powershell/Microsoft.PowerShell"

    envelope = etree.Element(SOAP_ENV + "Envelope", nsmap=NAMESPACE)
    envelope.append(header.to_dom())

    body = etree.Element(SOAP_ENV + "Body")
    envelope.append(body)

    return envelope


def create_command(shell_id, command, args=()):
    console_mode_stdin = True
    skip_cmd_shell = False

    header = Header(
        action='http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Command',  # NOQA
        shell_id=shell_id,
        options={
            "WINRS_CONSOLEMODE_STDIN": str(console_mode_stdin).upper(),
            "WINRS_SKIP_CMD_SHELL": str(skip_cmd_shell).upper(),
        }
    )

    body = etree.Element(SOAP_ENV + "Body")
    command_line = etree.SubElement(body, WIN_SHELL + "CommandLine")
    command_node = etree.SubElement(command_line, WIN_SHELL + "Command")
    command_node.text = command

    if args:
        arguments_node = etree.SubElement(command_line, WIN_SHELL + "Arguments")
        unicode_args = [
            a if isinstance(a, six.text_type) else a.decode('utf-8')
            for a in args
        ]
        arguments_node.text = u" ".join(unicode_args)

    return _wrap_envelope(header, body)


def cleanup_command(shell_id, command_id):
    """
    Clean-up after a command.
    """
    header = Header(
        action='http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Signal',  # NOQA
        shell_id=shell_id,
    )

    body = etree.Element(SOAP_ENV + "Body")
    signal = etree.SubElement(
        body, WIN_SHELL + "Signal", CommandId=command_id
    )
    code = etree.SubElement(signal, WIN_SHELL + "Code")
    code.text = 'http://schemas.microsoft.com/wbem/wsman/1/windows/shell/signal/terminate'  # NOQA

    return _wrap_envelope(header, body)


def parse_create_command_response(response):
    root = etree.fromstring(response)
    return _first_node_text(root, WIN_SHELL, 'CommandId')


def parse_create_shell_response(response):
    """
    TODO remove in favour of parse_create_shell_response_node
    """
    root = etree.fromstring(response)
    return _first_node_text(root, WIN_SHELL, 'ShellId')


def parse_create_shell_response_node(root):
    return _first_node_text(root, WIN_SHELL, 'ShellId')


def command_output(shell_id, command_id):
    header = Header(
        action='http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Receive',  # NOQA
        shell_id=shell_id,
    )

    body = etree.Element(SOAP_ENV + "Body")
    receive = etree.SubElement(body, WIN_SHELL + "Receive")
    desired_stream = etree.SubElement(
        receive, WIN_SHELL + "DesiredStream", CommandId=command_id
    )
    desired_stream.text = "stdout stderr"

    return _wrap_envelope(header, body)


def parse_soap_response(root):
    action = root.find(SOAP_ENV + "Header/" + ADDRESSING + "Action")
    if action is not None and action.text.endswith('fault'):
        fault = root.find(SOAP_ENV + "Body/" + SOAP_ENV + "Fault/" + SOAP_ENV + "Reason/" + SOAP_ENV + "Text")
        if fault is not None and fault.text:
            raise SoapException(fault.text)
        provider_fault = root.find('.//{http://schemas.microsoft.com/wbem/wsman/1/wsmanfault}ProviderFault')
        if provider_fault is not None and provider_fault.text:
            raise WsManException(provider_fault.text)
    return root


def parse_command_output(response):
    root = etree.fromstring(response)
    stream_nodes = [
        node for node in root.findall('.//*')
        if node.tag.endswith('Stream')
    ]

    buffer_stdout = []
    buffer_stderr = []
    return_code = None

    for stream_node in stream_nodes:
        if not stream_node.text:
            continue
        if stream_node.attrib['Name'] == 'stdout':
            buffer_stdout.append(
                base64.b64decode(stream_node.text.encode('ascii'))
            )
        elif stream_node.attrib['Name'] == 'stderr':
            buffer_stderr.append(
                base64.b64decode(stream_node.text.encode('ascii'))
            )

    # We may need to get additional output if the stream has not finished.
    # The CommandState will change from Running to Done like so:
    # @example
    #   from...
    #   <rsp:CommandState CommandId="..." #   State="http://schemas.microsoft.com/wbem/wsman/1/windows/shell/CommandState/Running"/>  # NOQA
    #   to...
    #   <rsp:CommandState CommandId="..." #   State="http://schemas.microsoft.com/wbem/wsman/1/windows/shell/CommandState/Done"> #   # NOQA
    #     <rsp:ExitCode>0</rsp:ExitCode>
    #   </rsp:CommandState>
    command_done = len([
        node for node in root.findall('.//*')
        if node.get('State', '').endswith('CommandState/Done')]) == 1

    if command_done:
        return_code = int(
            next(
                node for node in root.findall('.//*')
                if node.tag.endswith('ExitCode')
            ).text
        )

    return (
        b"".join(buffer_stdout), b"".join(buffer_stderr),
        return_code, command_done
    )


def get_streams(response_document):
    for stream_node in response_document.findall('.//' + WIN_SHELL + 'Stream'):
        if stream_node.text:
            stream_type = stream_node.attrib['Name']
            yield stream_type,  stream_node.text


