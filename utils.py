import unicodedata
import json
import asyncio
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms as CipherAlgorithms, modes as CipherModes
from typing import Any

from console_utils import *
from config import *
from message import Message

settings_template = """{
    "username": "",
    "allow-embeds": true,
    "encryption-level": 1,
    "log-chat-history": true
}"""

cache = {
    "settings": None
}

def sanitize_text(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0]!="C" or ch == '\n')

def debug_print(*args: object, level: int = 2, **kwargs: dict[str, object]):
    if DEBUG_LEVEL >= level:
        print_with_timestamp(*args, **kwargs)

def generate_backup_settings_file():
    try:
        with open('./data/settings.json', 'w') as file:
            template = json.loads(settings_template)
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
        debug_print("Failed to access 'data/settings.json'", level=1)
        generate_backup_settings_file()
        return get_setting(setting)
    except RuntimeError as e:
        debug_print("RuntimeError:", e, level=1)
    except Exception as e:
        debug_print("Exception:", e, level=1)
        generate_backup_settings_file()
        return get_setting(setting)
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
        debug_print("ERROR: Failed to save settings:", e, level=1)
    finally:
        return success

def change_username(username: str):
    if not validate_username(username):
        raise RuntimeError("Invalid username.")
    set_setting('username', username)

def get_current_username() -> str:
    username: Any = get_setting("username")
    assert(isinstance(username, str))
    return username

def validate_username(username: Any) -> bool:
    if type(username) != type("str"):
        return False
    if len(username) < 3 or len(username) > 20:
        return False
    if not username.isprintable():
        return False
    if username in RESERVED_USERNAMES:
        return False
    return True

def generate_key(offset: int = 2, modulo: int = 65500):
    return (secrets.randbelow(modulo * 3) + offset) % modulo

async def send_unencrypted_data(text_data: str, address: str, port: int):
    debug_print("Initiating unencrypted connection.")
    writer = None
    try:
        _, writer = await asyncio.open_connection(address, port)
        writer.write(json.dumps({"unencrypted_message": text_data}).encode())
        writer.write_eof()
        await writer.drain()
        debug_print("Successfully sent the unencrypted message.")
        return True
    except:
        debug_print("Unencrypted connection failed.")
        return False
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()

async def send_encrypted_data_with_common_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int) -> bool:
    debug_print("Initiating common DH key exchange")
    writer = None
    writer2 = None
    try:
        # generate our public key
        our_public_key = (DEFAULT_DH_G ** our_private_key) % DEFAULT_DH_P

        # establish connection
        reader, writer = await asyncio.open_connection(address, port)

        # send our oublic key
        writer.write(json.dumps({"key": str(our_public_key)}).encode())
        writer.write_eof()
        await writer.drain()

        # read their public key
        data = await asyncio.wait_for(reader.read(), timeout=10)
        decoded_data = json.loads(data.decode())
        peer_public_key = int(decoded_data["key"])

        # check if the key has any issues
        assert(peer_public_key > 0 and peer_public_key < DEFAULT_DH_P)

        # generate a shared key using our private key and their public key
        shared_key: int = (peer_public_key ** our_private_key) % DEFAULT_DH_P

        # encrypt the data using the shared key
        encrypted_data = encrypt_data(data_to_send.encode(), shared_key)

        # send the encrypted message
        _, writer2 = await asyncio.open_connection(address, port)
        writer2.write(json.dumps({"encrypted_message": str(encrypted_data)}).encode())
        writer2.write_eof()
        await writer2.drain()
        debug_print("Successfully sent the encrypted message.")
        return True
    except:
        debug_print("Common DH failed.")
        return False
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
        if writer2:
            writer2.close()
            await writer2.wait_closed()

async def send_encrypted_data_with_custom_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int, g: int, p: int) -> bool:
    debug_print("Initiating custom DH key exchange")
    writer = None
    writer2 = None
    try:
        # generate our public key
        our_public_key = (g ** our_private_key) % p
        debug_print("Our private key:", our_private_key)
        debug_print("Our public key:", our_public_key)

        # establish connection
        reader, writer = await asyncio.open_connection(address, port)
        debug_print("Connected to", writer.get_extra_info('peername'))

        # send our oublic key along with our custom g and p
        g_str = str(g)
        p_str = str(p)
        writer.write(json.dumps({
                "key": str(our_public_key),
                "g": g_str, "base": g_str,
                 "p": p_str, "mod": p_str, "modulus": p_str, "prime": p_str,
                }).encode())
        writer.write_eof()
        await writer.drain()
        debug_print("Sent public key")

        # read their public key
        data = await asyncio.wait_for(reader.read(), timeout=10)
        debug_print("Received peer's public key")
        decoded_data: dict = json.loads(data.decode()) # type: ignore
        peer_public_key = int(decoded_data["key"]) # type: ignore
        peer_dh_params = extract_diffie_hellman_parameters_from_dict(decoded_data)

        # check if the key has any issues and if the peer supports our custom g and p values
        assert(peer_public_key > 0 and peer_public_key < p)
        assert(peer_dh_params["g"] == g)
        assert(peer_dh_params["p"] == p)

        debug_print("Agreed on DH parameters. g:", g, ", p:", p)

        # generate a shared key using our private key and their public key
        shared_key: int = (peer_public_key ** our_private_key) % p
        debug_print("Shared key:", shared_key)

        # encrypt the data using the shared key
        encrypted_data = encrypt_data(data_to_send.encode(), shared_key)

        # send the encrypted message
        _, writer2 = await asyncio.open_connection(address, port)
        writer2.write(json.dumps({"encrypted_message": str(encrypted_data)}).encode())
        writer2.write_eof()
        await writer2.drain()
        debug_print("Successfully sent the encrypted message.")
        return True
    except Exception:
        debug_print("Custom DH failed.")
        return False
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
        if writer2:
            writer2.close()
            await writer2.wait_closed()

async def send_encrypted_data_with_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int, g: int = DEFAULT_DH_G, p: int = DEFAULT_DH_P) -> int:
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

def encrypt_data(data: bytes, key: int) -> bytes:
    cipher = Cipher(CipherAlgorithms.TripleDES(key=str(key).encode().ljust(24)), CipherModes.CBC(b''))
    encryptor = cipher.encryptor()
    return encryptor.update(data)

def get_decrypted_data(data: bytes, key: int) -> bytes:
    cipher = Cipher(CipherAlgorithms.TripleDES(key=str(key).encode().ljust(24)), CipherModes.CBC(b''))
    deencryptor = cipher.decryptor()
    return deencryptor.update(data)

def search_dict(dictionary: Any, keys: list[str]) -> object|None:
    for k in dictionary.keys():
        v = dictionary[k]
        if k in keys:
            return v
        if isinstance(v, dict):
            result = search_dict(v, keys)
            if result:
                return result
    return None

def extract_diffie_hellman_parameters_from_dict(dictionary: Any, default_g: int = DEFAULT_DH_G, default_p: int = DEFAULT_DH_P):
    g = search_dict(dictionary, ["g", "G", "dh_g", "base"])
    p = search_dict(dictionary, ["p", "P", "dh_p", "mod", "modulo", "prime"])
    result = {'g': default_g, 'p': default_p}
    if isinstance(g, str) or isinstance(g, int):
        result["g"] = int(g)
    if isinstance(p, str) or isinstance(p, int):
        result["p"] = int(p)
    return result

def log_chat_message(message: Message):
    if get_setting("log-chat-history"):
        text = "Date: %s, Author: %s, Message: %s" % (time.ctime(), message.get_author_username(), message.get_text_content())
        text = text.replace('\033[', "ESC [")
        text = text.replace('\033]', "ESC ]")
        text = text.replace('\033', "ESC")
        text = text.replace('\a', "BELL")
        text = text.replace('\\', "\\\\")
        text = text.replace('\n', "\\n")
        text = text.replace('\t', "\\t")
        text = text.strip()
        with open("message_history.log", '+a') as file:
            file.write(text + '\n')