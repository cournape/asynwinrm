NS_XML = "http://www.w3.org/XML/1998/namespace"
NS_SOAP_ENV = "http://www.w3.org/2003/05/soap-envelope"
NS_ADDRESSING = "http://schemas.xmlsoap.org/ws/2004/08/addressing"
NS_CIMBINDING = "http://schemas.dmtf.org/wbem/wsman/1/cimbinding.xsd"
NS_ENUM = "http://schemas.xmlsoap.org/ws/2004/09/enumeration"
NS_TRANSFER = "http://schemas.xmlsoap.org/ws/2004/09/transfer"
NS_WSMAN_DMTF = "http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd"
NS_WSMAN_MSFT = "http://schemas.microsoft.com/wbem/wsman/1/wsman.xsd"
# NS_SCHEMA = "http://www.w3.org/2001/XMLSchema"
NS_SCHEMA_INST = "http://www.w3.org/2001/XMLSchema-instance"
NS_WIN_SHELL = "http://schemas.microsoft.com/wbem/wsman/1/windows/shell"
NS_WSMAN_FAULT = "http://schemas.microsoft.com/wbem/wsman/1/wsmanfault"

NAMESPACE = {
    "env": NS_SOAP_ENV,
    "a": NS_ADDRESSING,
    "b": NS_CIMBINDING,
    "n": NS_ENUM,
    "x": NS_TRANSFER,
    "w": NS_WSMAN_DMTF,
    "p": NS_WSMAN_MSFT,
    #"xsd": NS_SCHEMA,
    "xsi": NS_SCHEMA_INST,
    "rsp": NS_WIN_SHELL,
    "f": NS_WSMAN_FAULT,
}

SOAP_ENV = "{%s}" % (NS_SOAP_ENV,)
WSMAN_DMTF = "{%s}" % (NS_WSMAN_DMTF,)
WSMAN_MSFT = "{%s}" % (NS_WSMAN_MSFT,)
ADDRESSING = "{%s}" % (NS_ADDRESSING,)
WIN_SHELL = "{%s}" % (NS_WIN_SHELL,)
WSMAN_FAULT = "{%s}" % (NS_WSMAN_FAULT,)


XML = "{%s}"  % (NS_XML,)
