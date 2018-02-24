from enum import Enum


class RunspacePoolState(Enum):
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