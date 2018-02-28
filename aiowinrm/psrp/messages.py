"""
def session_capability_message(runspace_pool_id)
  Message.new(
    runspace_pool_id,
    Message::MESSAGE_TYPES[:session_capability],
    render('session_capability')
  )
end

# Creates a new init runspace pool PSRP message.
# @param runspace_pool_id [String] The UUID of the remote shell/runspace pool.
def init_runspace_pool_message(runspace_pool_id)
  Message.new(
    runspace_pool_id,
    Message::MESSAGE_TYPES[:init_runspacepool],
    render('init_runspace_pool')
  )
end

# Creates a new PSRP message that creates pipline to execute a command.
# @param runspace_pool_id [String] The UUID of the remote shell/runspace pool.
# @param pipeline_id [String] The UUID to correlate the command/pipeline
# response.
# @param command [String] The command passed to Invoke-Expression.
def create_pipeline_message(runspace_pool_id, pipeline_id, command)
  Message.new(
    runspace_pool_id,
    Message::MESSAGE_TYPES[:create_pipeline],
    render('create_pipeline', command: command.encode(xml: :text)),
    pipeline_id
  )
end

private

# Renders the specified template with the given context
# @param template [String] The base filename of the PSRP message template.
# @param context [Hash] Any options required for rendering the template.
# @return [String] The rendered XML PSRP message.
# @api private
def render(template, context = nil)
  template_path = File.expand_path(
    "#{File.dirname(__FILE__)}/#{template}.xml.erb")
  template = File.read(template_path)
  Erubis::Eruby.new(template).result(context)
end

"""
import textwrap
import lxml.etree as etree

from aiowinrm.psrp.init_runspace_xml import INIT_RUNSPACE_XML
from aiowinrm.psrp.message import Message
from aiowinrm.psrp.pipeline_xml import get_pipeline_xml

REMOVE_BLANKS_PARSER = etree.XMLParser(remove_blank_text=True)


def xml_remove_spaces(inp):
    root = etree.fromstring(inp, parser=REMOVE_BLANKS_PARSER)
    return etree.tostring(root).decode('utf-8')


def create_session_capability_message(runspace_id):
    message_data = textwrap.dedent("""\
    <Obj RefId="0">
      <MS>
        <Version N="protocolversion">2.3</Version>
        <Version N="PSVersion">2.0</Version>
        <Version N="SerializationVersion">1.1.0.1</Version>
      </MS>
    </Obj>
    """)
    # message_data = xml_remove_spaces(message_data)
    return Message(runspace_id, message_type='session_capability', data=message_data)


def init_runspace_pool_message(runspace_id):
    return Message(runspace_id, message_type='init_runspacepool', data=INIT_RUNSPACE_XML)


def create_pipeline_message(runspace_id, pipeline_id, script):
    return Message(runspace_id,
                   message_type='create_pipeline',
                   data=get_pipeline_xml(script),
                   pipeline_id=pipeline_id)
