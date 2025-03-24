import base64
import json

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
        self._content = content
        self._filename = sanitize_filename(filename)
    def get_sanitized_filename(self) -> str:
        return self._filename
    def get_content(self) -> bytes:
        return self._content
    def get_base64encoded_content(self) -> bytes:
        return base64.b64encode(self._content)
    def __str__(self):
        return json.dumps({
            "filename": self.get_sanitized_filename(),
            "base64_content": str(self.get_base64encoded_content())
        })