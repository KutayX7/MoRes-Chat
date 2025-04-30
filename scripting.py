import os
import copy
import threading
import uuid

import utils
import message_server
from message import Message
from message_packet import MessagePacket
from user import User, Users

# The custom environment for the scripts
# NOTE: This part is not meant to be secure in any way. Scripts can import modules.
# TODO: Add more methods
ENV = {
    '__builtins__': __builtins__,
    '__name__': '__main__',

    # python functions
    'filter': filter,
    'map': map,
    'print': print,
    'type': type,

    # types
    'float': float,
    'int': int,
    'list': list,
    'object': object,
    'str': str,
    'tuple': tuple,

    # App API
    'get_active_users': lambda: list(filter(lambda user: user.is_active(), [user for user in Users.get_all_users()])),
    'get_current_user': lambda: Users.get_user_by_username(utils.get_current_username()),
    'get_setting': utils.get_setting,
    'set_setting': utils.set_setting,
    'send_message': lambda user, text: message_server.outbound_message_queue.put(MessagePacket(Message('<localhost>', text), [user])),
    'send_system_message': lambda text: message_server.push_inbound_message(MessagePacket(Message('<system>', text), ['<localhost>'])),
}

def run_script(script_name: str, *args) -> str:
    if not os.path.exists('./user_scripts/'):
        return 'Folder `user_scripts`, does not exist.'
    if '..' in script_name or '/' in script_name or '\\' in script_name or '~' in script_name:
        raise RuntimeError('Invalid script name.')
    path = os.path.abspath('./user_scripts/' + script_name)
    if os.path.exists(path):
        try:
            with open(path) as script:
                content = script.read()
                env = copy.copy(ENV)
                env['args'] = copy.copy(args)
                thread = threading.Thread(None, exec, f'user_script/{script_name}.{str(uuid.uuid4())}', [content, env, env])
                thread.daemon = True
                thread.start()
            return ''
        except Exception as e:
            return 'Script failed to execute.'
    else:
        return f'Script `user_scripts/{script_name}` not found.'
