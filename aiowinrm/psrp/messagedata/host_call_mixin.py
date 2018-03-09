from aiowinrm.psrp.messagedata.message_data import MessageData


class HostCall(MessageData):

    @property
    def call_id(self):
        return int(self.first_with_n_prop('ci').text)

    @property
    def method_identifier(self):
        mi_node = self.first_with_n_prop('mi')
        return mi_node.find('ToString').text

    @property
    def method_parameters(self):
        mp_node = self.first_with_n_prop('mp')
        return mp_node.find('LST')

    @property
    def method_parameters_text(self):
        msgs = []
        for node in self.method_parameters:
            for string_node in node.findall('S'):
                msgs.append(string_node.text)
        return '\r\n'.join(msgs)