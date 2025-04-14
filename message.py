import copy

from attachment import Attachment

class Message():
    def __init__(self, author_username: str, text_content: str, attachments: list[Attachment] = [], metadata: dict[object, object] = {}):
        assert(type(author_username) == type(''))
        self._content = text_content
        self._author = author_username
        self._timestamp = 0
        self._attachments = attachments.copy()
        self._metadata = copy.deepcopy(metadata)
    def get_text_content(self) -> str:
        return str(self._content)
    def get_sender_username(self) -> str:
        return self._author
    def get_author_username(self) -> str:
        return self._author
    def get_attachments(self) -> list[Attachment]:
        return self._attachments.copy()
    def get_metadata(self):
        return copy.deepcopy(self._metadata)