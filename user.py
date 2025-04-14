import time

AUTO_CREATE_USERS = False

class User():
    def __init__(self, username: str):
        assert(username)
        assert(type(username) == type(''))
        self.username = username
        self._ip = 'NA'
        self._shared_key = 0
        self._last_seen = -1.0
    
    def has_ip(self):
        return self._ip != 'NA'
    def has_shared_key(self):
        return self._shared_key > 0
    
    def is_remote(self) -> bool:
        if self._ip not in ['127.0.0.1', '0.0.0.0', 'localhost', '::', '0::0']:
            return True
        return False
    def is_active(self) -> bool:
        return (self._last_seen + 10) > time.time()
    
    def set_ip(self, ip: str):
        self._ip = ip
    def set_shared_key(self, key: int):
        self._shared_key = key

    def update_last_seen(self):
        self._last_seen = time.time()
    
    def get_username(self):
        return self.username
    def get_ip(self) -> str:
        if self.has_ip():
            return self._ip
        raise AttributeError('User "' + self.username + '" does not have an IP address.')
    def get_shared_key(self) -> int:
        if self.has_shared_key():
            return self._shared_key
        raise AttributeError('User "' + self.username + '" and localhost do not have a shared key.')
    def get_last_seen(self) -> float:
        return self._last_seen
    
class Users():
    users: list[User] = []

    @staticmethod
    def create_user(username: str):
        if Users.check_username(username):
            raise RuntimeError('User "' + username + '" already exist.')
        user = User(username)
        user.update_last_seen()
        Users.users.append(user)
        return user

    @staticmethod
    def check_username(username: str) -> bool:
        for user in Users.users:
            if user.get_username() == username:
                return True
        return False

    @staticmethod
    def get_user_by_username(username: str) -> User:
        for user in Users.users:
            if user.get_username() == username:
                return user
        if AUTO_CREATE_USERS:
            Users.create_user(username)
        raise RuntimeError('User "' + username + '" not found')

    @staticmethod
    def get_user_by_ip(ip: str) -> User|None:
        best_last_seen = -1
        best_candidate = None
        for user in Users.users:
            if user.get_ip() == ip and user.get_last_seen() > best_last_seen:
                best_candidate = user
                best_last_seen = user.get_last_seen()
        if best_candidate == None:
            raise RuntimeWarning('No user found with the ip: ' + ip)
        return best_candidate

    @staticmethod
    def set_username_ip(username: str, ip: str):
        user: User = Users.get_user_by_username(username)
        user.set_ip(ip)

    @staticmethod
    def get_all_users():
        return Users.users.copy()
    
    @staticmethod
    def is_active(user: User|str) -> bool:
        if isinstance(user, str):
            user = Users.get_user_by_username(user)
        return user.is_active()
