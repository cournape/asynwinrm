from aiowinrm.psrp import remove_bom, strip_hex_white_space
from aiowinrm.psrp.messagedata.message_data import MessageData


class PipelineOutput(MessageData):

    @property
    def output(self):
        assert self.root.tag == 'S'
        return strip_hex_white_space(self.root.text)

    def get_raw_data(self):
        return remove_bom(self.raw.data)


