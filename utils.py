import unicodedata
import base64 as b64
import PIL
import PIL.Image
import json
import select
import sys
import os
import socket
import asyncio
from cryptography.fernet import Fernet
import re

from message import Message

ESC = '\033'
CSI = ESC + '['
FLUSH_ALLOWED = True
MAX_PACKET_SIZE = 4096
ALLOWED_CHARS_FOR_USERNAMES = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"

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
    "Bright White": 97,
}

cache = {
    "settings": None
}

def write(*values, flush: bool = FLUSH_ALLOWED):
    print(*values, end='', flush=flush)

def flush():
    print("", end='', flush=True)

def set_flush_allowed(flush: bool):
    global FLUSH_ALLOWED
    old_value = FLUSH_ALLOWED
    FLUSH_ALLOWED = flush
    return old_value

def set_cursor_YX(y: int, x: int):
    write(CSI + y + ';' + x + 'H')

def return_cursor_to_home():
    write(CSI + "0;0H")

def clear_current_line():
    write(CSI + "2K\r")

def setForegroundColor(color: int):
    write(CSI + str(color) + "m")

def setBackgroundColor(color: int):
    write(CSI + str(color + 10) + "m")

def resetColors():
    write(CSI + "0m")

def clear_window():
    write(CSI + "2J" + CSI + "3J")
    return_cursor_to_home()

def sanitize_text(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0]!="C" or ch == '\n')

def print_authored_text_message(message: Message):
    oldMode = FLUSH_ALLOWED
    set_flush_allowed(False)
    clear_current_line()
    setForegroundColor(COLORS["Yellow"])
    write(message.get_author_username() + ": ")
    setForegroundColor(COLORS["White"])
    write('\n> ' + sanitize_text(message.get_text_content()))
    resetColors()
    set_flush_allowed(oldMode)
    write('\n')


def packRGB(r, g, b):
    return (r * 65536 + g * 256 + b) // 1

def unpackRGB(c):
    r = c // 65536
    g = (c % 65536) // 256
    b = c % 256
    return (r, g, b)

# Embeds an (sixel) image in the terminal
# It was a pain the ass writing this and making it work on every sixel-supported terminal
def print_image(path):
    try:
        with PIL.Image.open(path) as image:
            image = image.convert("RGBA", colors=256)
            width, height = image.width, image.height
            encodedData = "\033Pq"
            colors = {}
            for y in range(0, height, 6):
                for x in range(width):
                    for i in range(min(y + 6, height) - 1, y - 1, -1):
                        (r, g, b, a) = image.getpixel((x, i))
                        p = packRGB(r, g, b)
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
                            (r, g, b, a) = image.getpixel((x, i))
                            p = packRGB(r, g, b)
                            mask *= 2
                            if p == c:
                                mask += 1
                        encodedData += chr(mask + 63)
                    encodedData += "$"
                encodedData = encodedData[:-1] + "-"
            encodedData = encodedData[:-1] + "\033\\"
            print(f'Image:{path} ({width}x{height}px): ' + encodedData)
    except:
        write(f'Image:{path}: Failed to load.\n')

def generate_backup_settings_file():
    try:
        with open('./data/settings.json', 'w') as file:
            template = json.loads('{"username": null, "allow-embeds": true, "e2ee": "DHE"}')
            json.dump(template, file)
    except:
        raise RuntimeError("Failed to access 'data/settings.json' file.")
    finally:
        cache["settings"] = None
    
def generate_new_keys_file():
    try:
        with open('./data/keys.json', 'w') as file:
            template = json.loads("{}")
            json.dump(template, file)
    except:
        raise RuntimeError("Failed to access 'data/keys.json' file.")
    finally:
        cache["keys"] = None

# TODO: Add better error handling
def get_setting(setting: str) -> object|None:
    if cache["settings"] != None:
        if setting in settings:
            return cache["settings"][setting]
    value = None
    try:
        with open('./data/settings.json', 'r') as file:
            settings = json.load(file)
        cache["settings"] = settings
        if setting in settings:
            value = settings[setting]
        else:
            raise RuntimeError(f'Setting {setting} not found in "data/settings.json"')
    except OSError:
        raise RuntimeError("Failed to access 'data/settings.json'.")
    except RuntimeError as e:
        print("ERROR:", e)
    except:
        generate_backup_settings_file()
        get_setting(setting)
    finally:
        return value

def set_setting(setting: str, value: object|None):
    success = False
    try:
        if cache["settings"] == None:
            with open('./data/settings.json', 'r') as file:
                cache["settings"] = json.load(file)
        settings = cache["settings"]
        settings[setting] = value
        with open('./data/settings.json', 'w') as file:
            json.dump(settings, file)
        success = True
    except Exception as e:
        print("WARNING: Failed to save settings:", e)
    finally:
        return success

def input_username() -> str:
    while True:
        name = input("Enter username: ")
        if len(name) >= 3 and len(name) <= 20 and name.isascii() and name.isprintable():
            valid = True
            for c in name:
                if c not in ALLOWED_CHARS_FOR_USERNAMES:
                    valid = False
                    break
            if name.count("_") > 1 or name[0] == '_' or name[-1] == '_':
                valid = False
            if valid:
                break
        print("You've entered an invalid or unsupported username. Usernames can only contain 3-20 alphanumeric English characters and optionally a single underscore somewhere in the middle.")
    return name

def get_current_username() -> str:
    return get_setting("username")

def send_data_TCP(address, port, data):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((address, port))
        sock.sendall(data)

def send_data_UDP(address, port, data):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.sendto(data, (address, port))

async def recv_all(sock: socket.socket, buffer_size=2048):
    data = b''
    while True:
        ready_to_read, _, _ = select.select([sock], [], [], 0)
        if ready_to_read:
            part = sock.recv(buffer_size)
            data += part
            if len(part) < buffer_size:
                break
        else:
            await asyncio.sleep(0.05)
    return data

async def send_encrypted_data_with_common_diffie_hellman(data_to_send: bytes, address, port, our_private_key) -> bytes:
    our_public_key = (2 ** our_private_key) % 19
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((address, port))
        sock.sendall(json.dumps({"key": str(our_public_key)}))
        data = await recv_all(sock)
        their_key = None
        decoded_data = json.loads(data)
        their_key = int(decoded_data["key"])
        assert(their_key > 0 and their_key < 19)
        shared_key: int = (their_key ** our_private_key) % 19
        f = Fernet(b64.b64encode(shared_key.to_bytes(32)))
        sock.sendall(json.dumps({"encrypted_message": str(f.encrypt(data_to_send))}))

async def send_encrypted_data_with_diffie_hellman(data_to_send: bytes, address, port, our_private_key, p, g) -> bytes:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((address, port))
            str_g = str(g)
            str_p = str(p)
            our_public_key = (g ** our_private_key) % p
            sock.sendall(json.dumps({
                "key": str(our_public_key),
                "g": str_g, "base": str_g,
                 "p": str_p, "mod": str_p, "modulus": str_p, "prime": str_p,
                }))
            data = await recv_all(sock)
            their_key = None
            decoded_data = json.loads(data)
            if "g" in decoded_data:
                assert(str(decoded_data["g"]) == str(g))
            if "p" in decoded_data:
                assert(str(decoded_data["p"]) == str(p))
            their_key = int(decoded_data["key"])
            assert(their_key > 0 and their_key < p)
            shared_key: int = (their_key ** our_private_key) % p
            f = Fernet(b64.b64encode(shared_key.to_bytes(32)))
            sock.sendall(json.dumps({"encrypted_message": str(f.encrypt(data_to_send))}))
            return True
    except: # if there is an issue, try again with the standard method
        try:
            await send_encrypted_data_with_common_diffie_hellman(data_to_send, address, port, our_private_key)
            return True
        except:
            return False

