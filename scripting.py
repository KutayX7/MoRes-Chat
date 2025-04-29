import os
import copy

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

    'print': utils.print_info,

    'map': map,
    'filter': filter,
    'float': float,
    'int': int,
    'list': list,
    'object': object,
    'str': str,
    'tuple': tuple,

    # App API
    'get_active_users': lambda: list(filter(lambda user: user.is_active(), [user for user in Users.get_all_users()])),
    'get_setting': utils.get_setting,
    'set_setting': utils.set_setting,
    'send_message': lambda user, text: message_server.outbound_message_queue.put(MessagePacket(Message('<localhost>', text), [user])),
}

def run_script(script_name: str, *args) -> bool:
    if '..' in script_name or '/' in script_name or '\\' in script_name or '~' in script_name:
        raise RuntimeError('Invalid script name.')
    path = os.path.abspath('./user_scripts/' + script_name)
    if os.path.exists(path):
        try:
            with open(path) as script:
                content = script.read()
                env = copy.copy(ENV)
                env['args'] = copy.copy(args)
                exec(content, env, env)
            return ''
        except Exception as e:
            return 'Script failed to execute.'
    else:
        return f'Script `user_scripts/{script_name}` not found.'