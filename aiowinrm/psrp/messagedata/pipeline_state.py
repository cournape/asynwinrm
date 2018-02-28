from enum import Enum

from aiowinrm.psrp.messagedata.error_record import ErrorRecord
from aiowinrm.psrp.messagedata.message_data import MessageData


class PipelineStateEnum(Enum):

    NOT_STARTED = 0
    RUNNING = 1
    STOPPING = 2
    STOPPED = 3
    COMPLETED = 4
    FAILED = 5
    DISCONNECTED = 6


class PipelineState(MessageData):

    @property
    def pipeline_state(self):
        return PipelineStateEnum(int(self.first_with_n_prop('PipelineState').text))

    @property
    def exception_as_error_record(self):
        if self.pipeline_state == PipelineStateEnum.FAILED:
            return ErrorRecord(self.raw)

if __name__ == '__main__':
    msg = """<?xml version="1.0" encoding="UTF-8"?>
    <Obj RefId="0">
       <MS>
          <I32 N="PipelineState">3</I32>
          <Obj N="ExceptionAsErrorRecord" RefId="1">
             <TN RefId="0">
                <T>System.Management.Automation.ErrorRecord</T>
                <T>System.Object</T>
             </TN>
             <ToString>The pipeline has been stopped.</ToString>
             <MS>
                <Obj N="Exception" RefId="2">
                <TN RefId="1">
                   <T>System.Management.Automation.PipelineStoppedException</T>
                   <T>System.Management.Automation.RuntimeException</T>
                   <T>System.SystemException</T>
                   <T>System.Exception</T>
                   <T>System.Object</T>
                </TN>
                <ToString>System.Management.Automation.PipelineStoppedException: The pipeline has been stopped._x000D__x000A_ at
                System.Management.Automation.Internal.PipelineProcessor.SynchronousExecuteEnumerate(Object input, Hashtable errorResults, Boolean enumerate) in c:\\e\\win7_powershell\\admin\\monad\\src\\engine\\pipeline.cs:line 586</ToString>
                <Props>
                   <S N="ErrorRecord">The pipeline has been stopped.</S>
                   <S N="StackTrace">at
                System.Management.Automation.Internal.PipelineProcessor.SynchronousExecuteEnumerate(Object input, Hashtable errorResults, Boolean enumerate) in c:\\e\\win7_powershell\\admin\\monad\\src\\engine\\pipeline.cs:line 586</S>
                   <S N="Message">The pipeline has been stopped.</S>
                   <Obj N="Data" RefId="3">
                      <TN RefId="2">
                         <T>System.Collections.ListDictionaryInternal</T>
                         <T>System.Object</T>
                      </TN>
                      <DCT />
                   </Obj>
                   <Nil N="InnerException" />
                   <S N="TargetSite">System.Array SynchronousExecuteEnumerate(System.Object, System.Collections.Hashtable, Boolean)</S>
                   <Nil N="HelpLink" />
                   <S N="Source">System.Management.Automation</S>
                </Props>
                </Obj>
                <Nil N="TargetObject" />
                <S N="FullyQualifiedErrorId">PipelineStopped</S>
                <Nil N="InvocationInfo" />
                <I32 N="ErrorCategory_Category">14</I32>
                <S N="ErrorCategory_Activity" />
                <S N="ErrorCategory_Reason">PipelineStoppedException</S>
                <S N="ErrorCategory_TargetName" />
                <S N="ErrorCategory_TargetType" />
                <S N="ErrorCategory_Message">OperationStopped: (:) [], PipelineStoppedException</S>
                <B N="SerializeExtendedInfo">false</B>
             </MS>
          </Obj>
       </MS>
    </Obj>"""
    lines = msg.splitlines()[:]
    print(lines[21][7])
    pls = PipelineState(msg.encode('utf-8'))
    print(pls.pipeline_state)
