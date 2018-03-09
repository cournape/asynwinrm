from enum import Enum

from aiowinrm.psrp import strip_hex_white_space
from aiowinrm.psrp.messagedata.error_record import ErrorRecord
from aiowinrm.psrp.messagedata.host_call_mixin import HostCall
from aiowinrm.psrp.messagedata.message_data import MessageData
from aiowinrm.psrp.messagedata.pipeline_host_call import PipelineHostCall
from aiowinrm.psrp.messagedata.pipeline_output import PipelineOutput
from aiowinrm.psrp.messagedata.pipeline_state import PipelineState, PipelineStateEnum
from aiowinrm.psrp.messagedata.runspacepool_host_call import RunspacePoolHostCall
from aiowinrm.psrp.messagedata.runspacepool_state import RunspacePoolState
from aiowinrm.psrp.messagedata.session_capability import SessionCapability


class StreamTypeEnum(Enum):

    STD_OUT = 'std_out'
    STD_ERR = 'std_err'


class OutStream(object):

    def __init__(self, stream_type, text):
        self.stream_type = stream_type
        self.text = text


class PsOutputDecoder(object):

    MESSAGE_DATA_CLASSES = {
        'session_capability': SessionCapability,
        'runspacepool_state': RunspacePoolState,
        'runspacepool_host_call': RunspacePoolHostCall,
        'pipeline_state': PipelineState,
        'pipeline_host_call': PipelineHostCall,
        'pipeline_output': PipelineOutput,
        'error_record': ErrorRecord
    }

    @classmethod
    def get_stream(cls, decoded):
        if not decoded:
            return
        if not isinstance(decoded, MessageData):
            raise Exception('Expected MessageData')
        if decoded:
            if isinstance(decoded, PipelineOutput):
                return OutStream(StreamTypeEnum.STD_OUT, decoded.output)
            elif isinstance(decoded, HostCall):
                return OutStream(*cls.decode_call(decoded))
            elif isinstance(decoded, ErrorRecord):
                return cls.decode_error_record(decoded)
            elif isinstance(decoded, PipelineState) \
                    and decoded.pipeline_state == PipelineStateEnum.FAILED:
                return cls.decode_error_record(decoded.exception_as_error_record)

    @classmethod
    def decode_error_record(cls, err_msg):
        assert isinstance(err_msg, ErrorRecord)
        fq_err_id = err_msg.fully_qualified_error_id
        if fq_err_id == 'Microsoft.PowerShell.Commands.WriteErrorException':
            text = cls.fmt_err(f'{err_msg.invocation_info["line"]}: '
                               f'{err_msg.exception_message}',
                               err_msg)
        elif fq_err_id == 'NativeCommandError':
            text = cls.fmt_err(f'{err_msg.invocation_info["my_command"]}: '
                               f'{err_msg.exception_message}',
                               err_msg)
        elif fq_err_id == 'NativeCommandErrorMessage':
            text = cls.fmt_err(f'{err_msg.exception_message}',
                               err_msg)
        else:
            text = cls.fmt_err(f'{err_msg.exception_message}\r\n'
                               f'{err_msg.invocation_info["position_message"]}',
                               err_msg)
        return OutStream(StreamTypeEnum.STD_ERR,
                         strip_hex_white_space(text))

    @classmethod
    def fmt_err(cls, message_str, err_record):
        isinstance(err_record, ErrorRecord)
        return (f'{message_str}\r\n'
                f'CategoryInfo: {err_record.error_category_message}\r\n'
                f'FullyQualifiedErrorId\r\n{err_record.fully_qualified_error_id}')

    @classmethod
    def decode_call(cls, call_msg):
        text = None
        stream_type = StreamTypeEnum.STD_OUT
        assert isinstance(call_msg, HostCall)
        method_identifier = call_msg.method_identifier
        if 'WriteLine' in method_identifier:
            text = call_msg.method_parameters_text + '\r\n'
        elif method_identifier == 'WriteErrorLine':
            stream_type = StreamTypeEnum.STD_ERR
            text = call_msg.method_parameters_text + '\r\n'
        elif method_identifier == 'WriteDebugLine':
            text = f'Debug: {call_msg.method_parameters_text}\r\n'
        elif method_identifier == 'WriteWarningLine':  # make this STD_ERR or not?
            text = f'Warning: {call_msg.method_parameters_text}\r\n'
        elif method_identifier == 'WriteVerboseLine':
            text = f'Verbose: {call_msg.method_parameters_text}\r\n'
        elif method_identifier in ('Write1', 'Write2'):
            text = call_msg.method_parameters_text
        if text:
            return stream_type, strip_hex_white_space(text)

    @classmethod
    def decode(cls, message):
        if message.message_type_name in cls.MESSAGE_DATA_CLASSES:
            return cls.MESSAGE_DATA_CLASSES[message.message_type_name](message)
