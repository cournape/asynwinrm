from aiowinrm.psrp.init_runspace_xml import INIT_RUNSPACE_XML
from aiowinrm.psrp.message import Message
from aiowinrm.psrp.pipeline_xml import get_pipeline_xml
from aiowinrm.utils import xml_remove_spaces


CAP_XML = xml_remove_spaces("""\
<Obj RefId="0">
  <MS>
    <Version N="protocolversion">2.3</Version>
    <Version N="PSVersion">2.0</Version>
    <Version N="SerializationVersion">1.1.0.1</Version>
  </MS>
</Obj>
""")


def create_session_capability_message(runspace_id):
    return Message(runspace_id,
                   message_type='session_capability',
                   data=CAP_XML)


def init_runspace_pool_message(runspace_id):
    return Message(runspace_id,
                   message_type='init_runspacepool',
                   data=INIT_RUNSPACE_XML)


def create_pipeline_message(runspace_id, pipeline_id, script):
    return Message(runspace_id,
                   message_type='create_pipeline',
                   data=get_pipeline_xml(script),
                   pipeline_id=pipeline_id)
