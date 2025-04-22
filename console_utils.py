import time
from typing import Any

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

def print_with_timestamp(*args: *tuple[object], **kwargs: Any):
    print(time.ctime(), *args, **kwargs)
