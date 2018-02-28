from aiowinrm.psrp import remove_bom, strip_hex_white_space
from aiowinrm.psrp.messagedata.message_data import MessageData


class PipelineOutput(MessageData):

    @property
    def output(self):
        text = ''
        for node in self.root.find_all('//S'):
            if node.text:
                text += strip_hex_white_space(node.text)
            text += '\r\n'
        return text

    def get_raw_data(self):
        return remove_bom(self.raw.data)


