import config
import message_server
import utils
import scripting
from command import Command
from message import Message
from message_packet import MessagePacket

commands: list[Command] = []

def change_name(name: str) -> str:
    utils.change_username(name)
    return ("Your username has been successfully changed to " + name)

def exit(*args: *tuple[str]):
    import app
    app.exit_app()
    return "Goodbye!"

def command_help(*args: *tuple[str]) -> str:
    if len(args) > 0:
        command_name = args[0]
        for command in commands:
            if ('/' + command_name) in command.aliases:
                return "Command (" + command_name + ") usage:\n\t" + command.help
        return "Unknown command: " + command_name
    else:
        result = ["Available commands:\n  "]
        for command in commands:
            result.append(command.help)
            result.append('\n  ')
        return "".join(result)

def encryption_command(*args: *tuple[str]) -> str:
    g_set = False
    p_set = False
    for i in range(len(args)):
        argument = args[i]
        if '--fallback' == argument:
            config.FALLBACK_TO_PLAINTEXT = True
        if '--no-fallback' == argument:
            config.FALLBACK_TO_PLAINTEXT = True
        if '-0' == argument:
            config.DH_G = config.DEFAULT_DH_G
            config.DH_P = config.DEFAULT_DH_P
            config.PREFERRED_ENCRYPTION_LEVEL = 0
        if '-1' == argument:
            config.DH_G = config.DEFAULT_DH_G
            config.DH_P = config.DEFAULT_DH_P
            config.PREFERRED_ENCRYPTION_LEVEL = 1
        if '-2' == argument:
            config.PREFERRED_ENCRYPTION_LEVEL = 2
        if '-g' == argument:
            value = int(args[i+1])
            if value < 2:
                raise RuntimeError("Value of `g` must be greater than 1, prefereably 2.")
            config.DH_G = value
            g_set = True
        if '-p' == argument:
            value = int(args[i+1])
            if value < config.DH_G:
                raise RuntimeError("Value of `g` must be greater than `g`, and must be a prime number.")
            # TODO: Add prime check
            config.DH_P = value
            p_set = True
    if g_set or p_set:
        if config.PREFERRED_ENCRYPTION_LEVEL < 2:
            config.PREFERRED_ENCRYPTION_LEVEL = 2
    return "Encryption paramters have been set."

# TODO: Add option to restore most recent n messages
# TODO: Add options to filter messages
def restore_history(*args: *tuple[str]):
    try:
        with open('message_history.log', mode='r') as log:
            while True:
                line = log.readline()
                if len(line) > 40:
                    index_author = line.find('Author: ')
                    index_message = line.find('Message: ')
                    if index_message <= index_author:
                        continue
                    author = line[index_author+8:index_message-2]
                    text = line[index_message+9:]
                    if len(text) > 0 and author != '<system>':
                        if text[-1] == '\n':
                            text = text[:-1]
                        if text[-1] == '\r':
                            text = text[:-1]
                        message_server.inbound_message_queue.put(MessagePacket(Message(author, text), ['<localhost>']))
                else:
                    break
        return ""
    except:
        return "Failed to restore the message history."

def execute_script(*args: *tuple[str]) -> str:
    try:
        return scripting.run_script(args[0], *args[1:])
    except Exception as e:
        return str(e)

commands += [
    Command(command_help, ['/help', '/h'], "/help [command] : If provided, gives information about the specified command, otherwise returns information about all available commands. Aliases: /h"),
    Command(change_name, ['/username', '/u'], "/username <username> : Changes your username to <username>. Aliases: /u"),
    Command(execute_script, ['/exec'], "/exec <script_name> [arguments]... : Executes the script in the 'user_scripts' folder with the given arguments."),
    Command(exit, ['/exit', '/bye', '/goodbye'], "/exit : Closes the app. Aliases: /bye, /goodbye"),
    Command(encryption_command, ['/encryption', '/bye', '/goodbye'], "/encryption <parameter1> [parameter2]... : Sets encryption paramaters. These will not save between restarts.\n Parameters: \n\t -0 \t\t no encryption \n\t -1 \t\t default, diffie-hellman with preset g and p \n\t -2 \t\t diffie-hellman with custom g and p \n\t -g <N> \t\t sets DH_G to N \n\t -p <N> \t\t sets DH_P to N \n\t --fallback \t\t enabled by default, allows the connection to fallback to unencrypted plaintext \n\t --no-fallback \t\t opposite of --fallback"),
    Command(restore_history, ['/restorehistory', '/rh'], "/restorehistory : Restores the entire message history from the 'message_history.log' file. Aliases: /rh")
]

def run_command(text: str) -> bool:
    if len(text) < 2:
        return False
    for command in commands:
        result = None
        try:
            result = command.execute(text)
        except:
            break
        if (result != None) and (result != False):
            if isinstance(result, str) and len(result) > 0:
                message_server.generate_system_message(result)
            return True
    if text[0] == '/' and text[1] != ' ':
        message_server.generate_system_message("Unknown command. Please type '/help' for a list of available commands.")
    return False
