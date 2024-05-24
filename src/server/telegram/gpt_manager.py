import threading

from server.openai.chatgpt import ChatGPT


class ChatGPTManager:

    def __init__(self, telegram):
        self.telegram = telegram
        self.lock = threading.Lock()
        self.chatgpt_instances = {}

    def get_chatgpt(self, chatid) -> ChatGPT:
        with self.lock:
            if chatid not in self.chatgpt_instances or not self.chatgpt_instances[chatid].is_active():
                self.chatgpt_instances[chatid] = ChatGPT(self.telegram.user_manager.get_user(chatid))
                self.chatgpt_instances[chatid].start()
            return self.chatgpt_instances[chatid]

    def get_chatgpt_for_message(self, message) -> ChatGPT:
        return self.get_chatgpt(message['chat']['id'])

    def close(self):
        for instance in self.chatgpt_instances.values():
            instance.close()