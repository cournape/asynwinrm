from aiowinrm.psrp.messagedata.host_call_mixin import HostCall


class PipelineHostCall(HostCall):

    @property
    def exit_code(self):
        if self.method_parameters_text == 'SetShouldExit':
            lst_node = self.method_parameters
            return int(lst_node.find('I64').text)


if __name__ == '__main__':
    msg = """
    <Obj RefId="0">
          <MS>
            <I64 N="ci">1</I64>
            <Obj N="mi" RefId="1">
                <TN RefId="0"> <T>System.Management.Automation.Remoting.RemoteHostMethodId</T> <T>System.Enum</T>
                <T>System.ValueType</T>
                <T>System.Object</T>
                </TN> <ToString>ReadLine</ToString> <I32>11</I32>
            </Obj>
            <Obj N="mp" RefId="2">
              <TN RefId="1">
        <T>System.Collections.ArrayList</T>
                <T>System.Object</T>
              </TN>
              <LST />
            </Obj>
        </MS>
    </Obj>"""
    phc = PipelineHostCall(msg)
    print(phc.method_identifier)
    print(phc.method_parameters)
