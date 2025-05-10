import copy

from attachment import Attachment

class Message():
    def __init__(self, author_username: str, text_content: str, attachments: list[Attachment] = [], metadata: dict[str, object] = {}):
        assert(type(author_username) == type(''))
        self._content = text_content
        self._author = author_username
        self._timestamp = 0
        self._attachments = attachments.copy()
        self._metadata = copy.deepcopy(metadata)
    def has_attachments(self) -> bool:
        return len(self._attachments) > 0
    def has_metadata(self) -> bool:
        return len(self._metadata) > 0
    def get_text_content(self) -> str:
        return str(self._content)
    def get_sender_username(self) -> str:
        return self._author
    def get_author_username(self) -> str:
        return self._author
    def get_attachments(self) -> list[Attachment]:
        return self._attachments.copy()
    def get_metadata(self) -> dict[str, object]:
        return copy.deepcopy(self._metadata)