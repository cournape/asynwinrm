from aiowinrm.psrp.messagedata.message_data import MessageData


class SubscriptableNode(object):

    def __init__(self, node):
        self._node = node

    def __getitem__(self, item):
        nod = self._node.find(item)
        if nod:
            return nod.text


class ErrorRecord(MessageData):

    @property
    def exception(self):
        return self.property_dict('Exception')

    @property
    def exception_message(self):
        msg_nodes = self.root.findall(".//*[@N='Exception']/Props/S[@N='Message']")
        if msg_nodes:
            return msg_nodes[0].text

    @property
    def fully_qualified_error_id(self):
        return self.first_with_n_prop('FullyQualifiedErrorId').text

    @property
    def invocation_info(self):
        return self.property_dict('InvocationInfo')

    @property
    def error_category_message(self):
        return self.first_with_n_prop('ErrorCategory_Message').text

    @property
    def error_details_script_stack_trace(self):
        first = self.first_with_n_prop('ErrorDetails_ScriptStackTrace')
        if first:
            return first.text

    def property_dict(self, prop_name):
        return {
            node.attrib['N']: SubscriptableNode(node) if node.text else None
            for node in self.root.findall(".//*[@N='Exception']/Props/*")
        }


if __name__ == '__main__':
    msg = """<?xml version="1.0" encoding="UTF-8"?>
    <Obj RefId="0">
       <TN RefId="0">
          <T>System.Management.Automation.ErrorRecord</T>
          <T>System.Object</T>
       </TN>
       <ToString>Can't open file</ToString>
       <MS>
          <Obj N="Exception" RefId="1">
             <TN RefId="1">
                <T>System.IO.IOException</T>
                <T>System.SystemException</T>
                <T>System.Exception</T>
                <T>System.Object</T>
             </TN>
             <ToString>System.IO.IOException: Can't open file</ToString>
             <Props>
                <S N="Message">Can't open file</S>
                <Obj N="Data" RefId="2">
                   <TN RefId="2">
                      <T>System.Collections.ListDictionaryInternal</T>
                      <T>System.Object</T>
                   </TN>
                   <DCT />
                </Obj>
                <Nil N="InnerException" />
                <Nil N="TargetSite" />
                <Nil N="StackTrace" />
                <Nil N="HelpLink" />
                <Nil N="Source" />
             </Props>
          </Obj>
          <Nil N="TargetObject" />
          <S N="FullyQualifiedErrorId">System.IO.IOException</S>
          <Obj N="InvocationInfo" RefId="3">
             <TN RefId="3">
                <T>System.Management.Automation.InvocationInfo</T>
                <T>System.Object</T>
             </TN>
             <ToString>System.Management.Automation.InvocationInfo</ToString>
             <Props>
                <Obj N="MyCommand" RefId="4">
                   <TN RefId="4">
                      <T>System.Management.Automation.ScriptInfo</T>
                      <T>System.Management.Automation.CommandInfo</T>
                      <T>System.Object</T>
                   </TN>
                   <ToString>write-error -category OpenError -exception (new-object io.ioexception "Can't open file")</ToString>
                   <Props>
                      <SBK N="ScriptBlock">write-error -category OpenError -exception (new-object
    io.ioexception "Can't open file")</SBK>
                      <S N="Definition">write-error -category OpenError -exception (new-object
    io.ioexception "Can't open file")</S>
                      <S N="Name" />
                      <S N="CommandType">Script</S>
                      <S N="Visibility">Public</S>
                      <S N="ModuleName" />
                      <Nil N="Module" />
                      <Obj N="ParameterSets" RefId="5">
                         <TN RefId="5">
                            <T>System.Collections.ObjectModel.ReadOnlyCollection`1[[System.Management.Automation.CommandP arameterSetInfo, System.Management.Automation, Version=1.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35]]</T>
                            <T>System.Object</T>
                         </TN>
                         <LST>
                            <S />
                         </LST>
                      </Obj>
                   </Props>
                </Obj>
                <Obj N="BoundParameters" RefId="6">
                   <TN RefId="6">
                      <T>System.Collections.Generic.Dictionary`2[[System.String, mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089],[System.Object, mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089]]</T>
                      <T>System.Object</T>
                   </TN>
                   <DCT />
                </Obj>
                <Obj N="UnboundArguments" RefId="7">
                   <TN RefId="7">
                      <T>System.Collections.Generic.List`1[[System. Object, mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089]]</T>
                      <T>System.Object</T>
                   </TN>
                   <LST />
                </Obj>
                <I32 N="ScriptLineNumber">0</I32>
                <I32 N="OffsetInLine">0</I32>
                <S N="ScriptName" />
                <S N="Line" />
                <S N="PositionMessage" />
                <S N="InvocationName" />
                <I32 N="PipelineLength">1</I32>
                <I32 N="PipelinePosition">1</I32>
                <B N="ExpectingInput">false</B>
                <S N="CommandOrigin">Runspace</S>
             </Props>
          </Obj>
          <I32 N="ErrorCategory_Category">1</I32>
          <S N="ErrorCategory_Activity">Write-Error</S>
          <S N="ErrorCategory_Reason">IOException</S>
          <S N="ErrorCategory_TargetName" />
          <S N="ErrorCategory_TargetType" />
          <S N="ErrorCategory_Message">OpenError: (:) [Write-Error], IOException</S>
          <B N="SerializeExtendedInfo">true</B>
          <Ref N="InvocationInfo_BoundParameters" RefId="6" />
          <Obj N="InvocationInfo_CommandOrigin" RefId="8">
             <TN RefId="8">
                <T>System.Management.Automation.CommandOrigin</T>
                <T>System.Enum</T>
                <T>System.ValueType</T>
                <T>System.Object</T>
             </TN>
             <ToString>Runspace</ToString>
             <I32>0</I32>
          </Obj>
          <B N="InvocationInfo_ExpectingInput">false</B>
          <S N="InvocationInfo_InvocationName" />
          <S N="InvocationInfo_Line" />
          <I32 N="InvocationInfo_OffsetInLine">0</I32>
          <Obj N="InvocationInfo_PipelineIterationInfo" RefId="9">
             <TN RefId="9">
                <T>System.Int32[]</T>
                <T>System.Array</T>
                <T>System.Object</T>
             </TN>
             <LST>
                <I32>0</I32>
                <I32>0</I32>
             </LST>
          </Obj>
          <I32 N="InvocationInfo_PipelineLength">1</I32>
          <I32 N="InvocationInfo_PipelinePosition">1</I32>
          <S N="InvocationInfo_PositionMessage" />
          <I32 N="InvocationInfo_ScriptLineNumber">0</I32>
          <S N="InvocationInfo_ScriptName" />
          <Ref N="InvocationInfo_UnboundArguments" RefId="7" />
          <Obj N="CommandInfo_CommandType" RefId="10">
             <TN RefId="10">
                <T>System.Management.Automation.CommandTypes</T>
                <T>System.Enum</T>
                <T>System.ValueType</T>
                <T>System.Object</T>
             </TN>
             <ToString>Script</ToString>
             <I32>64</I32>
          </Obj>
          <S N="CommandInfo_Definition">write-error -category OpenError -exception (new-object io.ioexception "Can't open file")</S>
          <S N="CommandInfo_Name" />
          <Obj N="CommandInfo_Visibility" RefId="11">
             <TN RefId="11">
                <T>System.Management.Automation.SessionStateEntryVisibility</T>
                <T>System.Enum</T>
                <T>System.ValueType</T>
                <T>System.Object</T>
             </TN>
             <ToString>Public</ToString>
             <I32>0</I32>
          </Obj>
          <Obj N="PipelineIterationInfo" RefId="12">
             <TN RefId="12">
                <T>System.Collections.ObjectModel.ReadOnlyCollection`1[[System.Int32, mscorlib,
    Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089]]</T>
                <T>System.Object</T>
             </TN>
             <LST>
                <I32>0</I32>
                <I32>0</I32>
             </LST>
          </Obj>
          <Nil N="PSMessageDetails" />
       </MS>
    </Obj>"""
    err_rec = ErrorRecord(msg.encode('utf-8'))
    print('exception:', err_rec.exception)
    print('exception:', err_rec.exception_message)
    print('error_category_message:', err_rec.error_category_message)
    print('fully_qualified_error_id:', err_rec.fully_qualified_error_id)
    print('error_category_message:', err_rec.error_category_message)
    print('error_details_script_stack_trace:', err_rec.error_details_script_stack_trace)