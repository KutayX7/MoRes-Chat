import time

class User():
    def __init__(self, username: str):
        self.username = username
        self._ip = 'NA'
        self._shared_key = 0
        self._last_seen = 0

        self.update_last_seen()
    
    def has_ip(self):
        return self._ip != 'NA'
    def has_shared_key(self):
        return self._shared_key > 0
    
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
        raise AttributeError('User "' + self.username + '" and localhost do not have any share any keys.')
    def get_last_seen(self) -> float:
        return self._last_seen