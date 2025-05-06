import threading

from consts import DEFAULT_IMAGE_MODEL, DEFAULT_SPEECH_MODEL, DEFAULT_TRANSCRIBE_MODEL, IMAGE_MODELS, SPEECH_MODELS, IMAGE_SIZES, IMAGE_QUALITY, IMAGE_STYLE, IMAGE_BACKGROUND, SPEECH_VOICES, FEAT_SPEECH_INSTRUCTIONS


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
        self.image_model = DEFAULT_IMAGE_MODEL
        self.image_size = { model: IMAGE_MODELS[model][IMAGE_SIZES][0] for model in IMAGE_MODELS }
        self.image_quality = { model: IMAGE_MODELS[model][IMAGE_QUALITY][0] for model in IMAGE_MODELS if IMAGE_QUALITY in IMAGE_MODELS[model] }
        self.image_style = { model: IMAGE_MODELS[model][IMAGE_STYLE][0] for model in IMAGE_MODELS if IMAGE_STYLE in IMAGE_MODELS[model] }
        self.image_background = { model: IMAGE_MODELS[model][IMAGE_BACKGROUND][0] for model in IMAGE_MODELS if IMAGE_BACKGROUND in IMAGE_MODELS[model] }
        self.speech_model = DEFAULT_SPEECH_MODEL
        self.speech_instructions = { model: None for model in SPEECH_MODELS if SPEECH_MODELS[model].get(FEAT_SPEECH_INSTRUCTIONS, False) }
        self.speech_voice = { model: SPEECH_MODELS[model][SPEECH_VOICES][0] for model in SPEECH_MODELS }
        self.transcribe_model = DEFAULT_TRANSCRIBE_MODEL
        self.speech_all = False
        self.open_command = None

    def send_message(self, text):
        self.telegram._send_message(self.chatid, text)

    def send_reply(self, text):
        lines = text.splitlines()
        for i in range(0, len(lines), 100):
            self.send_message('\n'.join(lines[i:i+100]))
        if self.speech_all:
            self.telegram.whisper.create_tts(text, self.tts_model, self.tts_voice, lambda f: self.telegram._send_voice(self.chatid, f))

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
