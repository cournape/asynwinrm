

class AIOWinRMException(Exception):
    pass


class SoapException(Exception):
    pass


class SoapTimeout(SoapException):
    pass


class WsManException(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UnsupportedAuthArgument(Warning):
    pass


class AIOWinRMTransportError(Exception):
    pass