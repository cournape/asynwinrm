from enum import Enum


class AuthEnum(Enum):

    Basic = 'basic'
    NTLM = 'ntlm'
    Kerberos = 'kerberos'
    Auto = 'auto'
