from aiowinrm.psrp.messagedata.message_data import MessageData


class SessionCapability(MessageData):

    @property
    def protocol_version(self):
        return self.first_with_n_prop('protocolversion').text

    @property
    def ps_version(self):
        return self.first_with_n_prop('PSVersion').text

    @property
    def serialization_version(self):
        return self.first_with_n_prop('SerializationVersion').text


if __name__ == '__main__':
    sc = SessionCapability('<Obj RefId="0"><MS><Version N="protocolversion">2.2</Version><Version N="PSVersion">2.0</Version><Version N="SerializationVersion">1.1.0.1</Version></MS></Obj>')
    print(sc.protocol_version)
    print(sc.ps_version)
    print(sc.serialization_version)