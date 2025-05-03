import base64
import json
from typing import assert_type

def sanitize_filename(filename: str):
    result = filename
    while '/' in result:
        result = result[result.find('/')+1:]
    while '\\' in result:
        result = result[result.find('\\')+1:]
    while ".." in result:
        result = result[result.find("..")+1:]
    if result[0] == '.':
        result = filename[1:]
    if result[-1] == '.':
        result = filename[:-1]
    result = result.translate(dict.fromkeys(range(32)))
    return result

class Attachment():
    def __init__(self, filename: str, content: bytes):
        assert isinstance(filename, str), 'filename must be a str object'
        assert isinstance(content, bytes), 'filename must be a bytes object'
        self._content = content
        self._filename = sanitize_filename(filename)
    
    @staticmethod
    def from_str(string: str):
        decoded_oject = json.loads(string)
        return Attachment.from_dict(decoded_oject)
    @staticmethod
    def from_dict(dictionary: dict[str, str]):
        return Attachment(
            dictionary['filename'],
            base64.b64decode(dictionary['base64_content'].encode(encoding='ascii'))
        )
    
    def get_sanitized_filename(self) -> str:
        return sanitize_filename(self._filename)
    def get_content(self) -> bytes:
        return self._content
    def get_base64encoded_content(self) -> bytes:
        return base64.b64encode(self._content)
    def to_dict(self):
        return {
            "filename": self.get_sanitized_filename(),
            "base64_content": self.get_base64encoded_content().decode(encoding='ascii')
        }
    def __str__(self):
        return json.dumps(self.to_dict())