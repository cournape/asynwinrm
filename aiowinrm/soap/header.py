import uuid

import lxml.etree as etree

from attr import Factory, attr, attributes
from attr.validators import instance_of, optional

from .namespaces import (
    ADDRESSING, SOAP_ENV, WSMAN_DMTF, WSMAN_MSFT, XML
)


@attributes
class Header:
    action = attr()
    id = attr(default=Factory(uuid.uuid4))
    to = attr(default="http://windows-host:5985/wsman")
    reply_to = attr(default="http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous")
    max_envelope_size = attr(default=None, validator=optional(instance_of(int)))
    timeout = attr(default="PT60S")
    shell_id = attr(default=None, validator=optional(instance_of(str)))
    session_id = attr(default=None, validator=optional(instance_of(str)))
    resource_uri = attr(default="http://schemas.microsoft.com/wbem/wsman/1/windows/shell/cmd")
    options = attr(validator=instance_of(dict), default=Factory(dict))

    locale = attr(default="en-US")
    data_locale = attr(default="en-US")

    def to_dom(self):
        header = etree.Element(SOAP_ENV + "Header")

        action = etree.SubElement(
            header, ADDRESSING + "Action", mustUnderstand="true"
        )
        action.text = self.action

        if self.reply_to != "":
            reply_to = etree.SubElement(header, ADDRESSING + "ReplyTo")
            address = etree.SubElement(
                reply_to, ADDRESSING + "Address", mustUnderstand="true")
            address.text = self.reply_to

        if self.to != "":
            to = etree.SubElement(header, ADDRESSING + "To")
            to.text = self.to

        if self.timeout != "":
            timeout = etree.SubElement(header, WSMAN_DMTF + "OperationTimeout")
            timeout.text = self.timeout

        if self.resource_uri != "":
            resource_uri = etree.SubElement(
                header, WSMAN_DMTF + "ResourceURI", mustUnderstand="true"
            )
            resource_uri.text = self.resource_uri

        if self.max_envelope_size:
            max_envelop_size = etree.SubElement(
                header, WSMAN_DMTF + "MaxEnvelopeSize", mustUnderstand="true"
            )
            max_envelop_size.text = str(self.max_envelope_size)
        message_id = etree.SubElement(header, ADDRESSING + "MessageID")
        message_id.text = "uuid:{}".format(str(self.id))

        if self.session_id:
            session_id = etree.SubElement(header, ADDRESSING + "SessionId")
            session_id.text = "uuid:{}".format(str(self.session_id))

        if self.shell_id:
            selector_set = etree.SubElement(
                header, WSMAN_DMTF + "SelectorSet",
            )
            selector = etree.SubElement(
                selector_set, WSMAN_DMTF + "Selector", Name="ShellId"
            )
            selector.text = self.shell_id

        if len(self.options) > 0:
            option_set = etree.SubElement(header,  WSMAN_DMTF + "OptionSet")
            for name, text in self.options.items():
                option = etree.SubElement(
                    option_set, WSMAN_DMTF + "Option", Name=name
                )
                option.text = text

        if self.locale != "":
            locale = etree.SubElement(
                header, WSMAN_DMTF + "Locale", mustUnderstand="false",
            )
            locale.attrib[XML + "lang"] = self.locale

        if self.data_locale != "":
            locale = etree.SubElement(
                header, WSMAN_MSFT + "DataLocale", mustUnderstand="false",
            )
            locale.attrib[XML + "lang"] = self.data_locale

        return header
