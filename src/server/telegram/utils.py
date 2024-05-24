import threading
import time


class TelegramError(Exception):
    pass


class UpdateDeduplicator:

    def __init__(self):
        self.lock = threading.Lock()
        self.processed_updates = {}

    def deduplicate(self, update_id):
        with self.lock:
            if self.processed_updates.get(update_id, 0) + 60 * 60 * 24 > time.time():
                return True
            self.processed_updates[update_id] = time.time()
            return False
