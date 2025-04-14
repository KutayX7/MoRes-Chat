import shlex
from copy import copy
from typing import Callable

class Command:
    def __init__(self, callback: Callable[[*tuple[str]], str], alieases: list[str], help: str):
        self.callback = callback
        self.aliases = copy(alieases)
        self.help = help
    def execute(self, text: str) -> str|None:
        tokens = shlex.split(text)
        if len(tokens) < 1:
            return None
        command = tokens[0]
        if command not in self.aliases:
            return None
        args = tuple(tokens[1:])
        try:
            result = self.callback(*args)
            return result
        except Exception as e:
            return str(e) 
