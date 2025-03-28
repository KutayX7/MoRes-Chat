import unicodedata
import base64 as b64
import PIL.Image
import json
import select
import socket
import asyncio
import secrets
from cryptography.fernet import Fernet

from message import Message

ESC = '\033'
CSI = ESC + '['
FLUSH_ALLOWED = True
MAX_PACKET_SIZE = 4096
ALLOWED_CHARS_FOR_USERNAMES = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
RESERVED_USERNAMES = ["<system>", "localhost", "<localhost>"]

DEFAULT_DH_G = 2
DEFAULT_DH_P = 19
FALLBACK_TO_PLAINTEXT = False

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

# TODO: Add better error handling
def get_setting(setting: str) -> object|None:
    settings = cache["settings"]
    if settings != None:
        if setting in settings:
            return settings[setting]
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

def validate_username(username) -> bool:
    if type(username) != type("str"):
        return False
    if len(username) < 3:
        return False
    if not username.isprintable():
        return False
    if username in RESERVED_USERNAMES:
        return False
    return True

def generate_key(offset = 2, modulo = 65500):
    return (secrets.randbelow(modulo * 3) + offset) % modulo

async def send_unencrypted_data(text_data: str, address: str, port: int):
    try:
        reader, writer = await asyncio.open_connection(address, port)
        writer.write(json.dumps({"unencrypted_message": text_data}).encode())
        writer.drain()
        return True
    except:
        return False
    finally:
        if writer:
            writer.close()

async def send_encrypted_data_with_common_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int) -> bool:
    try:
        # generate our public key
        our_public_key = (DEFAULT_DH_G ** our_private_key) % DEFAULT_DH_P

        # establish connection
        reader, writer = await asyncio.open_connection(address, port)

        # send our oublic key
        writer.write(json.dumps({"key": str(our_public_key)}).encode())
        await writer.drain()

        # read their public key
        data = await reader.read()
        decoded_data = json.loads(data.decode())
        peer_public_key = int(decoded_data["key"])

        # check if the key has any issues
        assert(peer_public_key > 0 and peer_public_key < DEFAULT_DH_P)

        # generate a shared key using our private key and their public key
        shared_key: int = (peer_public_key ** our_private_key) % DEFAULT_DH_P

        # encrypt the data using the shared key
        f = Fernet(b64.b64encode(shared_key.to_bytes(32)))
        encrypted_data = f.encrypt(data_to_send.encode())

        # send the encrypted message
        writer.write(json.dumps({"encrypted_message": str(encrypted_data)}).encode())
        await writer.drain()
        return True
    except Exception as e:
        print("WARNING:", e)
        return False
    finally:
        if writer:
            writer.close()

async def send_encrypted_data_with_custom_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int, g: int, p: int) -> bool:
    try:
        # generate our public key
        our_public_key = (g ** our_private_key) % p

        # establish connection
        reader, writer = await asyncio.open_connection(address, port)

        # send our oublic key along with our custom g and p
        g_str = str(g)
        p_str = str(p)
        writer.write(json.dumps({
                "key": str(our_public_key),
                "g": g_str, "base": g_str,
                 "p": p_str, "mod": p_str, "modulus": p_str, "prime": p_str,
                }).encode())
        await writer.drain()

        # read their public key
        data = await reader.read()
        decoded_data: dict = json.loads(data.decode())
        peer_public_key = int(decoded_data["key"])
        peer_g_str = str(decoded_data.get("g", str(DEFAULT_DH_G)))
        peer_p_str = str(decoded_data.get("p", str(DEFAULT_DH_P)))

        # check if the key has any issues and if the peer supports our custom g and p values
        assert(peer_public_key > 0 and peer_public_key < p)
        assert(peer_g_str == g_str)
        assert(peer_p_str == p_str)

        # generate a shared key using our private key and their public key
        shared_key: int = (peer_public_key ** our_private_key) % p

        # encrypt the data using the shared key
        f = Fernet(b64.b64encode(shared_key.to_bytes(32)))
        encrypted_data = f.encrypt(data_to_send.encode())

        # send the encrypted message
        writer.write(json.dumps({"encrypted_message": str(encrypted_data)}).encode())
        await writer.drain()
        return True
    except Exception as e:
        print("WARNING:", e)
        return False
    finally:
        if writer:
            writer.close()

async def send_encrypted_data_with_diffie_hellman(data_to_send: bytes, address, port, our_private_key, g=DEFAULT_DH_G, p=DEFAULT_DH_P) -> int:
    success = await send_encrypted_data_with_custom_diffie_hellman(data_to_send, address, port, our_private_key, g=g, p=p)
    if success:
        return 2
    else:
        success = await send_encrypted_data_with_common_diffie_hellman(data_to_send, address, port, our_private_key)
        if success:
            return 1
        if FALLBACK_TO_PLAINTEXT:
            success = await send_unencrypted_data(data_to_send, address, port)
            if success:
                return 0
        return -1
    
def get_decrypted_data(data: bytes, key: int) -> str:
    f = Fernet(b64.b64encode(key.to_bytes(32)))
    return f.decrypt(data).decode()

async def async_filter(async_predicate, iterable):
    result = []
    for i in iterable:
        j = await async_predicate(i)
        if j:
            result.append(i)
    return result

async def async_map(async_func, iterable):
    result = []
    for i in iterable:
        j = await async_func(i)
        result.append(j)
    return result

async def is_prime(n):
    if n % 2 == 0:
        return n == 2
    if n % 3 == 0:
        return n == 3
    if n % 5 == 0:
        return n == 5
    if n % 11 == 0:
        return n == 11
    if n % 13 == 0:
        return n == 13
    if n % 7 == 0:
        return n == 7
    if n % 17 == 0:
        return n == 17
    if n % 19 == 0:
        return n == 19
    if n % 23 == 0:
        return n == 23
    for i in range(29, int((n**0.5) + 1.5), 2):
        if n % i == 0:
            return False
        elif i % 512 == 1:
            await asyncio.sleep(0.001)
    return True
