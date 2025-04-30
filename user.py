import time

class User():
    def __init__(self, username: str, local: bool):
        assert(username)
        assert(type(username) == type(''))
        self.username = username
        self._ip = 'NA'
        self._shared_key = 0
        self._last_seen = -1.0
        self._local = local
    
    def has_ip(self):
        return self._ip != 'NA'
    def has_shared_key(self):
        return self._shared_key > 0
    
    def is_local(self) -> bool:
        return self._local
    def is_remote(self) -> bool:
        return not self._local
    
    def is_active(self) -> bool:
        return (self._last_seen + 10) > time.time()
    
    def set_ip(self, ip: str):
        self._ip = ip
    def set_shared_key(self, key: int):
        self._shared_key = key
    def set_local(self):
        self._local = True
    def set_remote(self):
        self._local = False

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
    def create_user(username: str, local: bool):
        if Users.check_username(username):
            raise RuntimeError('User "' + username + '" already exist.')
        user = User(username, local)
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
        raise RuntimeError('User "' + username + '" does not exist')

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
    def rename_user(user: User|str, new_username: str):
        if not isinstance(new_username, str):
            raise Exception('Bad argument #2: `new_username` should be a str')
        if Users.check_username(new_username):
            raise RuntimeError(f'Another user already has the username "{new_username}"')
        if isinstance(user, str):
            user = Users.get_user_by_username(user)
        if isinstance(user, User):
            if not user.is_local():
                raise Exception('Can not rename an remote user')
            user.username = new_username

    @staticmethod
    def get_all_users():
        return Users.users.copy()
    
    @staticmethod
    def is_active(user: User|str) -> bool:
        if isinstance(user, str):
            user = Users.get_user_by_username(user)
        return user.is_active()
