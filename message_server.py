import socket
import json
import asyncio
import time
from queue import SimpleQueue

import utils
from message import Message
from message_packet import MessagePacket
from user import User, Users
from config import *

inbound_message_queue: SimpleQueue[MessagePacket] = SimpleQueue()
outbound_message_queue: SimpleQueue[MessagePacket] = SimpleQueue()
blocklist = {} # blocklisted addresses due to constantly sending malformed JSON packets

should_exit = False
ready_to_exit = False

def pull_inbound_message() -> MessagePacket|None:
    try:
        return inbound_message_queue.get_nowait()
    except:
        return None
def pull_outbound_message() -> MessagePacket|None:
    try:
        return outbound_message_queue.get_nowait()
    except:
        return None

def push_inbound_message(packet: MessagePacket):
    utils.log_chat_message(packet.message)
    inbound_message_queue.put(packet)

def generate_system_message(text: str):
    inbound_message_queue.put(MessagePacket(Message('<system>', text), ['<localhost>']))
    utils.debug_print("System message:", text)

# A wrapper for ease of use
class ChatConnection():
    def __init__(self, to_username: str, encryption: dict[str, int]|None = {"base": DH_G, "modulo": DH_P2 if PREFERRED_ENCRYPTION_LEVEL == 2 else DH_P}):
        self._user: User = Users.get_user_by_username(to_username)
        self._encrypted = False
        if encryption != None:
            self._encrypted = True
            self._g = encryption["base"]
            self._p = encryption["modulo"]
        self.reset_private_key()

    def reset_private_key(self):
        self._private_key = utils.generate_key()
    async def send_message(self, message: Message):
        ip = self._user.get_ip()
        if self._encrypted:
            result = await utils.send_encrypted_data_with_diffie_hellman(message.get_text_content(), ip, MESSAGING_PORT, self._private_key, self._p, self._g)
            if result == 1:
                self._p = DH_P
            elif result == 0:
                self._encrypted = False
            elif result == -1:
                generate_system_message("Failed to send the message.")
        else:
            await utils.send_unencrypted_data(message.get_text_content(), ip, MESSAGING_PORT)
        self.reset_private_key()

async def broadcast_send_service():
    while True:
        username = utils.get_current_username()
        if not utils.validate_username(username):
            utils.debug_print("WARNING: Detected invalid username.", level=1)
            generate_system_message("Please set a valid username with the '/username' command.")
        while not utils.validate_username(username):
            username = utils.get_current_username()
            await asyncio.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto((json.dumps({"username": username})).encode(), (SERVICE_BROADCAST_IP, SERVICE_BROADCAST_PORT))
            utils.debug_print("Sent service broadcast on", (SERVICE_BROADCAST_IP, SERVICE_BROADCAST_PORT))
        await asyncio.sleep(8)

def generate_online_message(user: User):
    generate_system_message("User %s is now online!" % user.get_username())

async def broadcast_recieve_service():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    sock.bind(('', DISCOVERY_PORT))
    utils.debug_print("Listening for service broadcast messages on port %d :" % (DISCOVERY_PORT), level=1)
    while not should_exit:
        try:
            data, (ip, port) = sock.recvfrom(256)
            utils.debug_print("Broadcast received from", ip, port)
            decoded_data = json.loads(data.decode())
            username = decoded_data["username"]
            assert(utils.validate_username(username))
            current_time = time.time()
            if Users.check_username(username):
                user: User = Users.get_user_by_username(username)
                if (user.get_last_seen() + SERVICE_BROADCAST_INTERVAL) > current_time:
                    if ip == user.get_ip():
                        user.set_ip(ip)
                        user.update_last_seen()
                        if not user.is_active():
                            generate_online_message(user)
                    else:
                        utils.debug_print("WARNING: Skipped suspicious broadcast. Old ip: %s, New address: %s." % (user.get_ip(), ip))
                else:
                    user.set_ip(ip)
                    user.update_last_seen()
            else:
                user = Users.create_user(username)
                user.set_ip(ip)
                user.update_last_seen()
        except OSError as e:
            pass # 99.9% socket blocking errors
        except Exception as e:
            utils.debug_print("Exception while handling incoming broadcast:", e)
        finally:
            await asyncio.sleep(0.1)

async def broadcast_service():
    asyncio.create_task(broadcast_recieve_service())
    asyncio.create_task(broadcast_send_service())
    
    while not should_exit:
        await asyncio.sleep(0.01)

async def handle_message_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        addr = writer.get_extra_info('peername')
        utils.debug_print("Incoming TCP request from", addr)
        ip: str = ''
        if len(addr) == 2:  # IPv4
            ip, _ = addr
        elif len(addr) == 4:  # IPv6
            ip, _, _, _ = addr
        else:
            raise RuntimeError("Unknown address type")
        if ip in blocklist:
            return
        user = Users.get_user_by_ip(ip)
        if not user:
            raise RuntimeError("Unknown user.")
        data = await reader.read(utils.MAX_PACKET_SIZE)
        message = data.decode(encoding='utf-8')
        decoded_object = json.loads(message)
        dh_params = utils.extract_diffie_hellman_parameters_from_dict(decoded_object, default_g=DH_G, default_p=DH_P)
        g, p = dh_params['g'], dh_params['p']
        if "key" in decoded_object: # diffie hellman key exhange + maybe encrypted message
            their_public_key = int(decoded_object["key"])
            private_key = utils.generate_key()
            public_key: int = (g ** private_key) % p
            shared_key: int = (their_public_key ** private_key) % p
            user.set_shared_key(shared_key)
            writer.write(json.dumps({"key": str(public_key)}).encode(encoding='utf-8'))
            writer.write_eof()
            await writer.drain()
        if "unencrypted_message" in decoded_object:
            text = decoded_object["unencrypted_message"]
            assert(type(text) == type(''))
            push_inbound_message(MessagePacket(Message(user.get_username(), text), ['<localhost>']))
        if "encrypted_message" in decoded_object:
            shared_key = user.get_shared_key()
            if not shared_key:
                return
            cypher_text = decoded_object["encrypted_message"]
            assert(isinstance(cypher_text, str))
            text = utils.get_decrypted_data(bytes(cypher_text, encoding="UTF-8"), shared_key).decode(encoding='utf-8')
            push_inbound_message(MessagePacket(Message(user.get_username(), text), ['<localhost>']))
    except Exception as e:
        utils.debug_print("Exception while handling TCP request:", e)
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()

async def outbound_message_server():
    while not should_exit:
        message_packet: MessagePacket|None = pull_outbound_message()
        if message_packet:
            for receiver in message_packet.get_outbound_receivers():
                try:
                    connection = ChatConnection(receiver)
                    await connection.send_message(message_packet.message)
                except Exception as e:
                    utils.debug_print("Exception while sending an outbound message:", e, level=1)
            if message_packet.is_inbound():
                push_inbound_message(message_packet)
            else:
                push_inbound_message(MessagePacket(message_packet.message, ['<localhost>']))
        await asyncio.sleep(0.01)

async def run_messaging_server():
    server = await asyncio.start_server(handle_message_client, '', MESSAGING_PORT)
    async with server:
        await server.start_serving()
        await outbound_message_server()

async def messaging_service():
    await run_messaging_server()

async def main():
    global ready_to_exit
    broadcast_service_task = asyncio.create_task(broadcast_service())
    messaging_service_task = asyncio.create_task(messaging_service())
    while not should_exit:
        await asyncio.sleep(0.01)
    await broadcast_service_task
    await messaging_service_task
    ready_to_exit = True

def exit():
    global should_exit
    should_exit = True

# NOTE: Normally, this module should not be used as main. This is for testing purposes only.
if __name__ == "__main__":
    asyncio.run(main())
