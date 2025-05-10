import socket
import json
import asyncio
import time
from queue import SimpleQueue

import utils
import events
from attachment import Attachment
from message import Message
from message_packet import MessagePacket
from user import User, Users
from config import *
from events import push_event, on_event

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
    push_event('on_inbound_message', packet.message)

def generate_system_message(text: str):
    inbound_message_queue.put(MessagePacket(Message('<system>', text), ['<localhost>']))
    utils.print_info("System message:", text)
    push_event('on_system_message', text)

# A wrapper for ease of use
class ChatConnection():
    def __init__(self, to_username: str):
        self._user: User = Users.get_user_by_username(to_username)
        self._encrypted = False
        if utils.get_setting('security.encryption.enabled', True):
            self._encrypted = True
            self._g = utils.get_setting('security.encryption.parameter.g', DEFAULT_DH_G)
            self._p = utils.get_setting('security.encryption.parameter.p', DEFAULT_DH_P)
        self.reset_private_key()

    def reset_private_key(self):
        self._private_key = utils.generate_key()
    async def send_message(self, message: Message):
        if not self._user.is_active():
            generate_system_message(f'Failed to send the message to {self._user.get_username()} because the user is offline.')
            return
        ip = self._user.get_ip()
        if self._encrypted:
            if utils.get_setting('security.encryption.forced', not FALLBACK_TO_PLAINTEXT):
                success = await utils.send_encrypted_message(message, ip, MESSAGING_PORT, self._private_key, g=self._g, p=self._p)
            else:
                success = await utils.send_encrypted_message_with_fallback(message, ip, MESSAGING_PORT, self._private_key, g=self._g, p=self._p)
            if not success:
                generate_system_message("Failed to send the message.")
        else:
            await utils.send_unencrypted_text(message.get_text_content(), ip, MESSAGING_PORT)
        self.reset_private_key()

async def broadcast_send_service():
    while True:
        username = utils.get_current_username()
        if not utils.validate_username(username):
            utils.print_warning("Detected invalid username.")
            generate_system_message("Please set a valid username with the '/username' command.")
        while not utils.validate_username(username):
            username = utils.get_current_username()
            await asyncio.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto((json.dumps({"username": username})).encode(), (SERVICE_BROADCAST_IP, SERVICE_BROADCAST_PORT))
            utils.print_info("Sent service broadcast on", (SERVICE_BROADCAST_IP, SERVICE_BROADCAST_PORT))
        await asyncio.sleep(8)

def generate_online_message(user: User):
    if user.is_remote():
        generate_system_message(f'User {user.get_username()} is now online!')
    push_event('on_user_online', user)

async def broadcast_recieve_service():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    sock.bind(('', DISCOVERY_PORT))
    utils.print_info("Listening for service broadcast messages on port %d :" % (DISCOVERY_PORT))
    while not should_exit:
        try:
            data, (ip, port) = sock.recvfrom(256)
            utils.print_info("Broadcast received from", ip, port)
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
                        utils.print_warning("Skipped suspicious broadcast. Old ip: %s, New address: %s." % (user.get_ip(), ip))
                else:
                    user.set_ip(ip)
                    user.update_last_seen()
            else:
                user = Users.create_user(username, local = utils.get_current_username() == username)
                user.set_ip(ip)
                user.update_last_seen()
                push_event('on_new_user', user)
                generate_online_message(user)
        except OSError as e:
            pass # 99.9% socket blocking errors
        except Exception as e:
            utils.print_error("Exception while handling incoming broadcast:", e)
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
        utils.print_info("Incoming TCP request from", addr)
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
        username: str = user.get_username()
        timeout = 5
        data = b''
        while True:
            data = data + await asyncio.wait_for(reader.read(MAX_PACKET_SIZE), timeout=timeout)
            timeout *= 0.99999 # to prevent large files (that can't be received in a short time) from being received
            # TODO: Do better and lighter checks
            if reader.at_eof():
                break
            try:
                json.loads(utils.decode_arbitrary_data(data))
                break
            except:
                pass
        decoded_data = utils.decode_arbitrary_data(data)
        decoded_object = json.loads(decoded_data)
        dh_params = utils.extract_diffie_hellman_parameters_from_dict(decoded_object, default_g=DH_G, default_p=DH_P)
        g, p = dh_params['g'], dh_params['p']
        if g != DEFAULT_DH_G:
            utils.print_info("Non-standard Diffie Hellman paramater, g: ", g)
        if p != DEFAULT_DH_P:
            utils.print_info("Non-standard Diffie Hellman paramater, p: ", p)
        if "key" in decoded_object: # diffie hellman key exhange + maybe encrypted message
            their_public_key = int(decoded_object["key"])
            private_key = utils.generate_key()
            public_key: int = (g ** private_key) % p
            shared_key: int = (their_public_key ** private_key) % p
            user.set_shared_key(shared_key)
            writer.write(json.dumps({"key": str(public_key), 'g': g, 'p': p}).encode(encoding='utf-8'))
            writer.write_eof()
            await writer.drain()
            try:
                if not (writer.is_closing() or reader.at_eof()): # in case if they still keep the connection
                    data2 = await asyncio.wait_for(reader.read(MAX_PACKET_SIZE), timeout=5)
                    decoded_data2 = utils.decode_arbitrary_data(data2)
                    decoded_object2 = json.loads(decoded_data2)
                    if 'encrypted_message' in decoded_object2:
                        decoded_object['encrypted_message'] = decoded_object2['encrypted_message']
                    if 'encrypted_attachments' in decoded_object2:
                        decoded_object['encrypted_attachments'] = decoded_object2['encrypted_attachments']
            except Exception as e2:
                pass
        text_content = ""
        attachments = list()
        metadata = dict()
        author = username
        if "unencrypted_message" in decoded_object:
            text = decoded_object["unencrypted_message"]
            assert(type(text) == type(''))
            text_content = text
        if "encrypted_message" in decoded_object:
            shared_key = user.get_shared_key()
            if shared_key:
                cypher_text = decoded_object["encrypted_message"]
                if isinstance(cypher_text, str):
                    text_content = utils.decrypt_text(cypher_text, shared_key)
        if 'attachments' in decoded_object:
            for attachment_dict in decoded_object['attachments']:
                if isinstance(attachment_dict, dict):
                    attachments.append(Attachment.from_dict(attachment_dict))
        if 'encrypted_attachments' in decoded_object:
            shared_key = user.get_shared_key()
            if shared_key:
                for encrypted_attachment in decoded_object['encrypted_attachments']:
                    if isinstance(encrypted_attachment, str):
                        attachments.append(Attachment.from_str(utils.decrypt_text(encrypted_attachment, shared_key)))
        if 'metadata' in decoded_object:
            if isinstance(decoded_object['metadata'], dict):
                metadata = decoded_object['metadata']
        if 'author' in decoded_object:
            if isinstance(decoded_object['author'], str):
                author = decoded_object['author']
                if Users.check_username(author):
                    user2 = Users.get_user_by_username(author)
                    if user2.has_ip() and user2.get_ip() == ip:
                        pass
                    else:
                        author = username
                else:
                    author = username
        message = Message(author, text_content, attachments, metadata)
        push_inbound_message(MessagePacket(message, ['<localhost>']))
    except Exception as e:
        utils.print_error("Exception while handling TCP request:", e)
    finally:
        if writer:
            await utils.close_stream(writer)

async def outbound_message_server():
    while not should_exit:
        message_packet: MessagePacket|None = pull_outbound_message()
        if message_packet:
            if message_packet.is_inbound():
                push_inbound_message(message_packet)
            async with asyncio.TaskGroup() as task_group:
                for receiver in message_packet.get_outbound_receivers():
                    if Users.check_username(receiver):
                        connection = ChatConnection(receiver)
                        task_group.create_task(connection.send_message(message_packet.message))
        else:
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

    events.on_event('ban_ip', lambda _, ip: isinstance(ip, str) and blocklist.setdefault(ip, 1))
    events.on_event('unban_ip', lambda _, ip: isinstance(ip, str) and blocklist.pop(ip, None))

    while not should_exit:
        await asyncio.sleep(0.01)
    await broadcast_service_task
    await messaging_service_task
    ready_to_exit = True

def exit():
    global should_exit
    should_exit = True

def _on_send_mesage_packet(_, message_packet):
    assert(isinstance(message_packet, MessagePacket))
    outbound_message_queue.put(message_packet)
on_event('send_message_packet', _on_send_mesage_packet)

# NOTE: Normally, this module should not be used as main. This is for testing purposes only.
if __name__ == "__main__":
    asyncio.run(main())
