from enum import Enum

from aiowinrm.psrp.messagedata.message_data import MessageData


class RunspacePoolStateEnum(Enum):

    BEFORE_OPEN = 0
    OPENING = 1
    OPENED = 2
    CLOSED = 3
    CLOSING = 4
    BROKEN = 5
    NEGOTIATION_SENT = 6
    NEGOTIATION_SUCCEEDED = 7
    CONNECTING = 8
    DISCONNECTED = 9


class RunspacePoolState(MessageData):

    @property
    def runspace_state(self):
        return RunspacePoolStateEnum(int(self.root.findall(".//*[@N='RunspaceState']")[0].text))


if __name__ == '__main__':
    msg = """
    <Obj RefId="1">
      <MS>
        <I32 N="RunspaceState">2</I32>
      </MS>
    </Obj>
    """
    md = RunspacePoolState(msg)
    print(md.runspace_state)