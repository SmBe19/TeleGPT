import threading

from server.openai.chat import AiChat


class ChatManager:

    def __init__(self, telegram):
        self.telegram = telegram
        self.lock = threading.Lock()
        self.chat_instances = {}

    def get_chat(self, chatid) -> AiChat:
        with self.lock:
            if chatid not in self.chat_instances or not self.chat_instances[chatid].is_active():
                self.chat_instances[chatid] = AiChat(self.telegram.user_manager.get_user(chatid))
                self.chat_instances[chatid].start()
            return self.chat_instances[chatid]

    def get_chat_for_message(self, message) -> AiChat:
        return self.get_chat(message['chat']['id'])

    def close(self):
        for instance in self.chat_instances.values():
            instance.close()
