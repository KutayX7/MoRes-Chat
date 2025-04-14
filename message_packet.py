import utils
from message import Message

class MessagePacket():
    def __init__(self, message: Message, receivers: list[str]):
        self.message = message
        self.receivers = receivers.copy()
    def is_inbound(self):
        return ('<localhost>' in self.receivers)
    def get_outbound_receivers(self):
        result: list[str] = []
        current_username = utils.get_current_username()
        for receiver in self.receivers:
            if utils.validate_username(receiver) and receiver != current_username:
                result.append(receiver)
        return result