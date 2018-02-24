from aiowinrm.psrp.message import Message


def capitalize(inp):
    if not inp:
        return inp
    return inp[0].upper() + inp[1:]


class MessageData(object):

    """
    module MessageData
      def self.parse(message)
        type_key = WinRM::PSRP::Message::MESSAGE_TYPES.key(message.type)
        type = camelize(type_key.to_s).to_sym
        const_get(type).new(message.data) if MessageData.constants.include?(type)
      end

      def self.camelize(underscore)
        underscore.split('_').collect(&:capitalize).join
      end
    end
    """

    def parse(self, message):
        assert isinstance(message, Message)
        type_key = Message.MESSAGE_TYPES

    def camelize(self, underscore):
        return ''.join(map(capitalize, underscore.split('_')))
