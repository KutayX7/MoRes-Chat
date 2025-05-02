import argparse

from constants import *

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug-level', help='set debug level [0, 2]', default=1, type=int, choices=[0, 1, 2])
args = parser.parse_args()

ICON_PATH = "./placeholder_app_icon_2_16x16.png"

INITIAL_SYSTEM_MESSAGE = "Type '/help' for a list of commands. To chat with other users, select them in the online users list. Only selected online users can receive your messages."

DEBUG_LEVEL = args.debug_level

# Username restrictions
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 20
RESERVED_USERNAMES = ["", ":", "<>", "system", "<system>", "<s>", "localhost", "<localhost>"]
BANNED_CHARS_FOR_USERNAMES = '\r\\:'

SERVICE_BROADCAST_IP = '255.255.255.255'
SERVICE_BROADCAST_PORT = 6000
SERVICE_BROADCAST_INTERVAL = 8.0 # in seconds
DISCOVERY_PORT = 6000
MESSAGING_PORT = 6001

MAX_PACKET_SIZE = 1024 * 8

# Diffie Hellman and enryption parameters
DH_G = DEFAULT_DH_G
DH_P = DEFAULT_DH_P
FALLBACK_TO_PLAINTEXT = True

# can fallback to unsecure mode if FALLBACK_TO_PLAINTEXT is set

TPS = 20 # ticks per second, range: [1, 250]