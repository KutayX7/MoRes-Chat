import time
from typing import Any
from config import *

ESC = '\033'
CSI = ESC + '['

COLORS = {
    "Black": 30,
    "Red": 31,
    "Green": 32,
    "Yellow": 33,
    "Blue": 34,
    "Magenta": 35,
    "Cyan": 36,
    "White": 37,
    "Bright Black": 90,
    "Bright Red": 91,
    "Bright Green": 92,
    "Bright Yellow": 93,
    "Bright Blue": 94,
    "Bright Magenta": 95,
    "Bright Cyan": 96,
    "Bright White": 97
}

def write(*args: str, **kwargs: Any):
    print(*args, end='', **kwargs)

def flush(**kwargs: Any):
    print("", end='', flush=True, **kwargs)

def set_cursor_YX(y: int, x: int, **kwargs: Any):
    write(CSI + str(y) + ';' + str(x) + 'H', **kwargs)

def return_cursor_to_home(**kwargs: Any):
    write(CSI + "0;0H", **kwargs)

def clear_current_line(**kwargs: Any):
    write(CSI + "2K\r", **kwargs)

def setForegroundColor(color: int, **kwargs: Any):
    write(CSI + str(color) + "m", **kwargs)

def setBackgroundColor(color: int, **kwargs: Any):
    write(CSI + str(color + 10) + "m", **kwargs)

def resetColors(**kwargs: Any):
    write(CSI + "0m", **kwargs)

def clear_window(**kwargs: Any):
    write(CSI + "2J" + CSI + "3J")
    return_cursor_to_home(**kwargs)

def print_with_timestamp(*args: *tuple[object], color: int|str|None = None, **kwargs: Any):
    setForegroundColor(COLORS['Blue'], flush=False)
    print(time.ctime(), **kwargs, flush=False, end=' ')
    resetColors(**kwargs, flush=False)
    if color != None:
        if isinstance(color, str):
            color = COLORS.get(color, 35)
        elif not isinstance(color, int):
            raise Exception(f'Invalid keyword argument: color. String or integer expected, got {type(color)}')
        setForegroundColor(color, flush=False)
    print(*args, **kwargs)
    resetColors(**kwargs)

def debug_print(*args: object, level: int = 2, **kwargs: dict[str, object]):
    if DEBUG_LEVEL >= level:
        print_with_timestamp(*args, **kwargs)

def print_error(*args: object, level: int = 1):
    print_with_timestamp("ERROR:", *args, color=COLORS['Red'])

def print_warning(*args: object, level: int = 1):
    print_with_timestamp("WARNING:", *args, color=COLORS['Yellow'])

def print_info(*args: object, level: int = 2):
    print_with_timestamp("INFO:", *args, color=COLORS['White'])