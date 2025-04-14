
ICON_PATH = "./placeholder_app_icon_2_16x16.png"

INITIAL_SYSTEM_MESSAGE = "Type '/help' for a list of commands. To chat with other users, select them in the online users list. Only selected online users can receive your messages."

DEBUG_LEVEL = 2
MAX_PACKET_SIZE = 4096

ALLOWED_CHARS_FOR_USERNAMES = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
RESERVED_USERNAMES = ["", ":", "<>", "system", "<system>", "<s>", "localhost", "<localhost>"]

SERVICE_BROADCAST_IP = '255.255.255.255'
SERVICE_BROADCAST_PORT = 6001
SERVICE_BROADCAST_INTERVAL = 8.0 # in seconds
DISCOVERY_PORT = 6001
MESSAGING_PORT = 6000

# Default Diffie Hellman and enryption parameters
DEFAULT_DH_G = 2
DEFAULT_DH_P = 19
DH_G = DEFAULT_DH_G
DH_P = DEFAULT_DH_P
DH_P2 = int("4958793475749573457394866757737484574858584658956895240863474895455346985801") # an alternative value for P, probably won't be supported by other peers
FALLBACK_TO_PLAINTEXT = True

PREFERRED_ENCRYPTION_LEVEL: int = 1 # 0: No encryption, 1 (default): Diffie-Hellman with default parameters, 2: Diffie-Hellman with custom parameters (P2)
# can fallback to unsecure mode if FALLBACK_TO_PLAINTEXT is set

TPS = 20 # ticks per second