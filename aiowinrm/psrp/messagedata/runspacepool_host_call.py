from aiowinrm.psrp.messagedata.host_call_mixin import HostCall


class RunspacePoolHostCall(HostCall):

    pass


if __name__ == '__main__':
    msg  = """
    <Obj RefId="0">
        <MS>
            <I64 N="ci">1</I64>
            <Obj N="mi" RefId="1">
                <TN RefId="0">
                    <T>System.Management.Automation.Remoting.RemoteHostMethodId</T>
                    <T>System.Enum</T>
                    <T>System.ValueType</T>
                    <T>System.Object</T>
                </TN>
                <ToString>ReadLine</ToString>
                <I32>11</I32>
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
    rhc = RunspacePoolHostCall(msg)
    print(rhc.call_id)
    print(rhc.method_identifier)
    print(rhc.method_parameters)