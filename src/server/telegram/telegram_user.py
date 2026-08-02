import json
import os
import threading

from consts import DATA_DIR, DEFAULT_SETTINGS


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
        # Lock is only needed to synchronize access to telegram
        self.lock = threading.Lock()
        self.settings = {}
        self.open_command = None
        self._load_settings()

        """
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
        self.transcribe_all = False
        """

    def send_message(self, text):
        self.telegram._send_message(self.chatid, text)

    def send_reply(self, text):
        lines = text.splitlines()
        for i in range(0, len(lines), 100):
            self.send_message('\n'.join(lines[i:i+100]))
        if self.get_setting('speech_all'):
            self.telegram.ai_audio.create_speech(text, self, lambda f: self.telegram._send_voice(self.chatid, f))

    def send_voice(self, voice_bytes):
        self.telegram._send_voice(self.chatid, voice_bytes)

    def send_photo(self, photo_bytes):
        self.telegram._send_photo(self.chatid, photo_bytes)

    def get_setting(self, key):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))

    def set_setting(self, key, value):
        self.settings[key] = value
        self._save_settings()

    def get_model_setting(self, model, key):
        return self.settings.get('models', {}).get(model, {}).get(key, DEFAULT_SETTINGS.get('models', {}).get(model, {}).get(key))

    def get_model_settings(self, model):
        return {
            **DEFAULT_SETTINGS.get('models', {}).get(model, {}),
            **self.settings.get('models', {}).get(model, {}),
        }

    def set_model_setting(self, model, key, value):
        if model not in self.settings.get('models', {}):
            self.settings.setdefault('models', {})[model] = {}
        self.settings['models'][model][key] = value
        self._save_settings()

    def _load_settings(self):
        data_path = os.path.join(DATA_DIR, f'{self.chatid}_settings.json')
        if os.path.exists(data_path):
            with open(data_path) as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

    def _save_settings(self):
        data_path = os.path.join(DATA_DIR, f'{self.chatid}_settings.json')
        with open(data_path, 'w') as f:
            json.dump(self.settings, f)

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
