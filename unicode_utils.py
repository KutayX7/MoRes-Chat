import re

# https://stackoverflow.com/a/40223212

_nonbmp = re.compile(r'[\U00010000-\U0010FFFF]')

def _surrogatepair(match: re.Match[str]) -> str:
    char = match.group()
    assert(ord(char) > 0xffff)
    encoded = char.encode('utf-16-le')
    return (
        chr(int.from_bytes(encoded[:2], 'little')) + 
        chr(int.from_bytes(encoded[2:], 'little')))

def with_surrogates(text: str) -> str:
    return _nonbmp.sub(_surrogatepair, text)