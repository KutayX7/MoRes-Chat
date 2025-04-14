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

# Embeds an (sixel) image in the terminal
# It was a pain the ass writing this and making it work on every sixel-supported terminal
# Even if this is not used anymore, my heart is still not letting me delete this
def print_image(path: str, **kwargs: Any):
    import PIL.Image
    try:
        with PIL.Image.open(path) as image: # type: ignore
            image = image.convert("RGBA", colors=256)
            width, height = image.width, image.height
            encodedData = "\033Pq"
            colors: dict[int, str] = {}
            for y in range(0, height, 6):
                for x in range(width):
                    for i in range(min(y + 6, height) - 1, y - 1, -1):
                        (r, g, b, a) = image.getpixel((x, i)) # type: ignore
                        p = packRGB(r, g, b) # type: ignore
                        if not p in colors:
                            if a < 1: #hehehehehehe
                                r, g, b = 0, 0, 0
                            colors[p] = f'{r*100//255};{g*100//255};{b*100//255}'
            for y in range(0, height, 6):
                for c in colors:
                    encodedData += f'#0;2;{colors[c]}#0'
                    for x in range(width):
                        mask = 0
                        for i in range(min(y + 6, height) - 1, y - 1, -1):
                            (r, g, b, a) = image.getpixel((x, i)) # type: ignore
                            p = packRGB(r, g, b) # type: ignore
                            mask *= 2
                            if p == c:
                                mask += 1
                        encodedData += chr(mask + 63)
                    encodedData += "$"
                encodedData = encodedData[:-1] + "-"
            encodedData = encodedData[:-1] + "\033\\"
            print(f'Image:{path} ({width}x{height}px): ' + encodedData, **kwargs)
    except:
        write(f'Image:{path}: Failed to load.\n', **kwargs)

def packRGB(r: int, g: int, b: int):
    return (r * 65536 + g * 256 + b) // 1

def unpackRGB(c: int):
    r = c // 65536
    g = (c % 65536) // 256
    b = c % 256
    return (r, g, b)
