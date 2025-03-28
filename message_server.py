import socket
import json
import asyncio
import time
from queue import SimpleQueue

import utils
from message import Message
from message_packet import MessagePacket
from user import User, Users

SERVICE_BROADCAST_IP = '192.168.0.255'
SERVICE_BROADCAST_PORT = 6001
SERVICE_BROADCAST_INTERVAL = 8.0
DISCOVERY_PORT = 6001
MESSAGING_PORT = 6000

DH_G = 2
DH_P = 19
DH_P2 = int("4958793475749573457394866757737484574858584658956895240863474895455346985801") # made this up :P

inbound_message_queue: SimpleQueue[MessagePacket] = SimpleQueue()
outbound_message_queue: SimpleQueue[MessagePacket] = SimpleQueue()
blocklist = {} # blocklisted addresses due to constantly sending malformed JSON packets
host = socket.gethostname()

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
    
def generate_system_message(text: str):
    inbound_message_queue.put(MessagePacket(Message('<system>', text), ['<localhost>']))

# A wrapper for ease of use
class ChatConnection():
    def __init__(self, to_username, encryption={"base": DH_G, "modulo": DH_P2}):
        self._user: User = Users.get_user_by_username(to_username)
        self._encrypted = False
        if encryption != None:
            self._encrypted = True
            self._g = encryption["base"]
            self._p = encryption["modulo"]
        self.reset_private_key()

    def reset_private_key(self) -> int:
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
        assert(type(username) == type("string")) # just in case if the setting is corrupt
        if not utils.validate_username(username):
            generate_system_message("Please set a valid username in 'data/settings.json' and restart the program.")
        while not utils.validate_username(username):
            username = utils.get_current_username()
            await asyncio.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto((json.dumps({"username": username})).encode(), (SERVICE_BROADCAST_IP, SERVICE_BROADCAST_PORT))
        await asyncio.sleep(8)

def generate_online_message(user: User):
    generate_system_message("User %s is now online!" % user.get_username())

async def broadcast_recieve_service():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    sock.bind((socket.gethostname(), SERVICE_BROADCAST_PORT))
    print("Listening for service broadcast messages on UDP port", SERVICE_BROADCAST_PORT)
    while not should_exit:
        try:
            data, (ip, port) = sock.recvfrom(256)
            decoded_data = json.loads(data.decode())
            username = decoded_data["username"]
            assert(utils.validate_username(username))
            current_time = time.time()
            if Users.check_username(username):
                user: User = Users.get_user_by_username(username)
                if ((user.get_last_seen() + SERVICE_BROADCAST_INTERVAL) > current_time) and (ip != user.get_ip()): # suspiciously early request from a different address, better not save the new ip yet
                    print("WARNING: Skipped suspicious broadcast. Old ip: %s, New address: %s." % (user.get_ip(), ip))
                else:
                    user.set_ip(ip)
                    user.update_last_seen()
            else:
                user = Users.create_user(username)
                user.set_ip(ip)
                user.update_last_seen()
                generate_online_message(user)
        except OSError:
            pass
        except Exception as e:
            print("Exception:", e)
        finally:
            await asyncio.sleep(0.1)

async def broadcast_service():
    recv_task = asyncio.create_task(broadcast_recieve_service())
    send_task = asyncio.create_task(broadcast_send_service())
    
    while not should_exit:
        await asyncio.sleep(0.01)

async def handle_message_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        addr = writer.get_extra_info('peername')
        if len(addr) == 2:  # IPv4
            ip, port = addr
        elif len(addr) == 4:  # IPv6
            ip, port, flowinfo, scopeid = addr
        else:
            raise RuntimeError("Unknown address type")
        if ip in blocklist:
            return
        user: User = Users.get_user_by_ip(ip)
        data = await reader.read()
        message = data.decode()
        decoded_object = json.loads(message)
        g, p = DH_G, DH_P
        if "g" in decoded_object:
            g = int(decoded_object["g"])
        if "p" in decoded_object:
            p = int(decoded_object["p"])
        if "key" in decoded_object: # diffie hellman key exhange + encrypted message
            their_public_key = int(decoded_object["key"])
            private_key = utils.generate_key()
            public_key = (g ** private_key) % p
            shared_key = (their_public_key ** private_key) % p
            user.set_shared_key(shared_key)
            writer.write(json.dumps({"key": str(public_key)}).encode())
            await writer.drain()
            data2 = await asyncio.wait_for(reader.read(), 1)
            message2 = data2.decode()
            decoded_object2 = json.loads(message2)
            if "encrypted_message" in decoded_object2:
                cypher_text = decoded_object2["encrypted_message"]
                assert(type(cypher_text) == type(''))
                text = utils.get_decrypted_data(bytes(cypher_text), shared_key)
                inbound_message_queue.put(MessagePacket(Message(user.get_username(), text), ['<localhost>']))
        if "unencrypted_message" in decoded_object:
            text = decoded_object["unencrypted_message"]
            assert(type(text) == type(''))
            inbound_message_queue.put(MessagePacket(Message(user.get_username(), text), ['<localhost>']))
    except:
        pass
    finally:
        if writer:
            writer.close()

async def outbound_message_server():
    while not should_exit:
        message_packet: MessagePacket|None = pull_outbound_message()
        if message_packet:
            for receiver in message_packet.get_outbound_receivers():
                try:
                    connection = ChatConnection(receiver)
                    await connection.send_message(message_packet)
                except:
                    pass
            if message_packet.is_inbound():
                inbound_message_queue.put(message_packet)
            else:
                inbound_message_queue.put(MessagePacket(message_packet.message, ['<localhost>']))
        else:
            await asyncio.sleep(0.1)


async def run_messaging_server():
    server = await asyncio.start_server(handle_message_client, 'localhost', MESSAGING_PORT)
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
