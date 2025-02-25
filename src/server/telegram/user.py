import threading

from consts import DALLE_MODELS


class TelegramUserManager:

    def __init__(self, telegram):
        self.telegram = telegram
        self.lock = threading.Lock()
        self.user_instances = {}

    def get_user(self, chatid):
        with self.lock:
            if chatid not in self.user_instances:
                self.user_instances[chatid] = TelegramUser(self.telegram, chatid)
            return self.user_instances[chatid]

    def is_chat_known(self, chatid):
        with self.lock:
            return chatid in self.user_instances

    def get_user_for_message(self, message):
        return self.get_user(message['chat']['id'])


class TelegramUser:

    def __init__(self, telegram, chatid):
        self.telegram = telegram
        self.chatid = chatid
        self.lock = threading.Lock()
        self.dalle_model = DALLE_MODELS[0]
        self.dalle2_size = '256x256'
        self.dalle3_size = '1024x1024'
        self.dalle3_quality = 'standard'
        self.dalle3_style = 'natural'
        self.dalle_prompt = False
        self.dalle_imgurl = False
        self.tts_model = 'tts-1'
        self.tts_voice = 'echo'
        self.tts_all = False
        self.open_command = None

    def send_message(self, text):
        self.telegram._send_message(self.chatid, text)

    def send_reply(self, text):
        lines = text.splitlines()
        for i in range(0, len(lines), 100):
            self.send_message('\n'.join(lines[i:i+100]))
        if self.tts_all:
            self.telegram.whisper.create_tts(text, self.tts_model, self.tts_voice, lambda f: self.telegram._send_voice(self.chatid, f))

    def dalle_size(self):
        if self.dalle_model == 'dall-e-2':
            return self.dalle2_size
        elif self.dalle_model == 'dall-e-3':
            return self.dalle3_size
        else:
            raise ValueError()

    def set_dalle_size(self, size):
        if self.dalle_model == 'dall-e-2':
            self.dalle2_size = size
        elif self.dalle_model == 'dall-e-3':
            self.dalle3_size = size
        else:
            raise ValueError()

    def available_dalle_sizes(self):
        if self.dalle_model == 'dall-e-2':
            return ['256x256', '512x512', '1024x1024']
        elif self.dalle_model == 'dall-e-3':
            return ['1024x1024', '1792x1024', '1024x1792']
        else:
            raise ValueError()

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

