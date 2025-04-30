import unicodedata
import json
import asyncio
import secrets
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives.ciphers import Cipher, modes as CipherModes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from typing import Any
from tkinter import Variable

from console_utils import *
from config import *
from message import Message
from constants import *

_cache = {
    "settings": None
}

_setting_bindings: dict[str, list[Variable]] = {}

def sanitize_text(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0]!="C" or ch == '\n')

def generate_backup_settings_file():
    try:
        with open('./data/settings.json', 'w') as file:
            template = json.loads("{}")
            json.dump(template, file)
    except:
        raise RuntimeError("Failed to access 'data/settings.json' file.")
    finally:
        _cache["settings"] = None

def get_setting(setting: str, default: int|float|str|bool) -> object:
    settings = _cache["settings"]
    value = default
    if settings != None:
        if setting in settings:
            value = settings[setting]
    else:
        try:
            with open('./data/settings.json', 'r') as file:
                settings = json.load(file)
            _cache["settings"] = settings
            if setting in settings:
                value = settings[setting]
        except OSError:
            print_error("Failed to access 'data/settings.json'")
            generate_backup_settings_file()
            return get_setting(setting, default=default)
        except RuntimeError as e:
            print_error("RuntimeError:", e)
        except Exception as e:
            print_error("Exception:", e)
            generate_backup_settings_file()
            return get_setting(setting, default=default)
    
    if type(value) != type(default):
        set_setting(setting, default)
        print_error(f'Setting "{setting}" type mismatch. Replacing it with the default value of {default}.')
        return default
    
    return value

def set_setting(setting: str, value: object|None):
    success = False
    try:
        if _cache["settings"] == None:
            with open('./data/settings.json', 'r') as file:
                _cache["settings"] = json.load(file)
        settings = _cache["settings"]
        settings[setting] = value
        with open('./data/settings.json', 'w') as file:
            json.dump(settings, file, indent=4, sort_keys=True)
        success = True
        if _setting_bindings.get(setting) != None:
            for variable in _setting_bindings[setting]:
                variable.set(value)
    except Exception as e:
        print_error("Failed to save settings:", e)
    return success

def bind_variable_to_setting(variable: Variable, setting: str, default: int|float|str|bool) -> Variable:
    if _setting_bindings.get(setting) == None:
        _setting_bindings[setting] = []
    _setting_bindings[setting].append(variable)
    variable.set(get_setting(setting, default))
    return variable

def change_username(username: str):
    if not validate_username(username):
        raise RuntimeError("Invalid username.")
    set_setting('username', username)

def get_current_username() -> str:
    username: str = get_setting("username", '')
    return username

def validate_username(username: Any) -> bool:
    if type(username) != type("str"):
        return False
    if len(username) < MIN_USERNAME_LENGTH or len(username) > MAX_USERNAME_LENGTH:
        return False
    if not username.isprintable():
        return False
    if username in RESERVED_USERNAMES:
        return False
    return True

def generate_key(offset: int = 2, modulo: int = 65500):
    return (secrets.randbelow(modulo * 3) + offset) % modulo

async def send_unencrypted_data(text_data: str, address: str, port: int) -> bool:
    print_info("Initiating unencrypted connection.")
    writer = None
    try:
        _, writer = await asyncio.open_connection(address, port)
        writer.write(json.dumps({"unencrypted_message": text_data}).encode(encoding='utf-8'))
        writer.write_eof()
        await writer.drain()
        print_info("Successfully sent the unencrypted message.")
        return True
    except:
        print_error("Unencrypted connection failed.")
        return False
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()

async def send_encrypted_data_with_common_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int) -> bool:
    print_info("Initiating common DH key exchange")
    writer = None
    writer2 = None
    try:
        # generate our public key
        our_public_key = (DEFAULT_DH_G ** our_private_key) % DEFAULT_DH_P

        # establish connection
        reader, writer = await asyncio.open_connection(address, port)

        # send our oublic key
        writer.write(json.dumps({"key": str(our_public_key)}).encode(encoding='utf-8'))
        writer.write_eof()
        await writer.drain()

        # read their public key
        data = await asyncio.wait_for(reader.read(), timeout=10)
        decoded_data = json.loads(data.decode(encoding='utf-8'))
        peer_public_key = int(decoded_data["key"])

        # check if the key has any issues
        assert(peer_public_key > 0 and peer_public_key < DEFAULT_DH_P)

        # generate a shared key using our private key and their public key
        shared_key: int = (peer_public_key ** our_private_key) % DEFAULT_DH_P

        # encrypt the data using the shared key
        encrypted_data: str = encrypt_text(data_to_send, shared_key)

        # send the encrypted message
        _, writer2 = await asyncio.open_connection(address, port)
        writer2.write(json.dumps({"encrypted_message": encrypted_data}).encode())
        writer2.write_eof()
        await writer2.drain()
        print_info("Successfully sent the encrypted message.")
        return True
    except Exception as e:
        print_error("Common DH failed. Error:", e)
        return False
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
        if writer2:
            writer2.close()
            await writer2.wait_closed()

async def send_encrypted_data_with_custom_diffie_hellman(data_to_send: str, address: str, port: int, our_private_key: int, g: int, p: int) -> bool:
    print_info("Initiating custom DH key exchange")
    print_info("G:", g, " P:", p)
    writer = None
    writer2 = None
    try:
        # generate our public key
        our_public_key = (g ** our_private_key) % p
        print_info("Our private key:", our_private_key)
        print_info("Our public key:", our_public_key)

        # establish connection
        reader, writer = await asyncio.open_connection(address, port)
        print_info("Connected to", writer.get_extra_info('peername'))

        # send our oublic key along with our custom g and p
        g_str = str(g)
        p_str = str(p)
        writer.write(json.dumps({
                "key": str(our_public_key),
                "g": g_str, "base": g_str,
                 "p": p_str, "mod": p_str, "modulus": p_str, "prime": p_str,
                }).encode(encoding='utf-8'))
        writer.write_eof()
        await writer.drain()
        print_info("Sent public key")

        # read their public key
        data = await asyncio.wait_for(reader.read(), timeout=10)
        print_info("Received peer's public key")

        # decode data
        decoded_data: dict = json.loads(data.decode(encoding='utf-8')) # type: ignore

        # extract parameters
        peer_public_key = int(decoded_data["key"]) # type: ignore
        peer_dh_params = extract_diffie_hellman_parameters_from_dict(decoded_data)

        print_info("Peer's public key: ", peer_public_key)

        # check if the key has any issues and if the peer supports our custom g and p values
        if peer_dh_params["g"] != g:
            raise RuntimeError(f'Peer g parameter mismatch. ({g}-{peer_dh_params["g"]})')
        elif peer_dh_params["p"] != p:
            raise RuntimeError(f'Peer p parameter mismatch. ({p}-{peer_dh_params["p"]})')
        elif peer_public_key < 1:
            raise RuntimeError(f'Peer public key ({peer_public_key}) is less than 1')
        elif peer_public_key >= p:
            raise RuntimeError(f'Peer public key ({peer_public_key}) is bigger than p ({p})')

        print_info("Agreed on DH parameters. g:", g, ", p:", p)

        # generate a shared key using our private key and their public key
        shared_key: int = (peer_public_key ** our_private_key) % p
        print_info("Shared key:", shared_key)

        # encrypt the data using the shared key
        encrypted_data = encrypt_text(data_to_send, shared_key)

        # send the encrypted message
        _, writer2 = await asyncio.open_connection(address, port)
        writer2.write(json.dumps({"encrypted_message": encrypted_data}).encode())
        writer2.write_eof()
        await writer2.drain()
        print_info("Successfully sent the encrypted message.")
        return True
    except Exception as e:
        print_error("Custom DH failed. Error:", e)
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

def encrypt_text(text: str, key: int) -> str:
    cipher = Cipher(TripleDES(key=str(key).encode().ljust(24)), CipherModes.ECB())
    encryptor = cipher.encryptor()
    encoded_text = text.encode(encoding='utf-8')
    encrypted_data = encryptor.update(pad_PKCS7(encoded_text)) + encryptor.finalize()
    encrypted_string = b64encode(encrypted_data).decode(encoding='ascii')
    test_unencrypted_string = decrypt_text(encrypted_string, key)

    if text != test_unencrypted_string:
        print_error("Encryption failed to preserve data. Result: ", test_unencrypted_string)
        raise Exception("Encryption failed to preserve data.")
    return encrypted_string

def decrypt_text(encrypted_text: str, key: int) -> str:
    cipher = Cipher(TripleDES(key=str(key).encode().ljust(24)), CipherModes.ECB())
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(b64decode(encrypted_text.encode(encoding='ascii'))) + decryptor.finalize()
    return unpad_PKCS7(decrypted_data).decode(encoding='utf-8')

def pad_PKCS7(data: bytes):
    padder = PKCS7(64).padder()
    padded_data = padder.update(data) + padder.finalize()
    return padded_data

def unpad_PKCS7(data: bytes):
    unpadder = PKCS7(64).unpadder()
    unpadded_data = unpadder.update(data) + unpadder.finalize()
    return unpadded_data

def search_dict(dictionary: dict, keys: list[str]) -> object|None:
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
    if get_setting('chat.log.enabled', default=True):
        text = "Date: %s, Author: %s, Message: %s" % (time.ctime(), message.get_author_username(), message.get_text_content())
        text = text.replace('\033[', "ESC [")
        text = text.replace('\033]', "ESC ]")
        text = text.replace('\033', "ESC")
        text = text.replace('\a', "BELL")
        text = text.replace('\\', "\\\\")
        text = text.replace('\n', "\\n")
        text = text.replace('\t', "\\t")
        text = text.strip()
        try:
            with open("message_history.log", '+a', encoding='utf-8') as file:
                file.write(text + '\n')
        except:
            print_error("Failed to log the message.")