import abc

CAT_BASICS = 1000
CAT_TEXT = 2000
CAT_THREADS = 3000
CAT_IMAGES = 4000
CAT_AUDIO = 5000
CAT_TRANSCRIBE = 6000
CAT_ADVANCED = 9000

telegram_commands = {}
telegram_callbacks = {}


def command(description, order):
    def inner(f):
        f.__description__ = description
        f.__sort_order__ = order
        telegram_commands[f.__name__] = f
        return f

    return inner


def callback(cmd):
    def inner(f):
        telegram_callbacks[cmd] = f
        return f

    return inner


class TelegramCommands(abc.ABC):

    def __init__(self):
        self.model_manager = None
        self.chat_manager = None
        self.user_manager = None

    @abc.abstractmethod
    def _reply(self, message, reply):
        ...

    @abc.abstractmethod
    def _reply_keyboard(self, message, reply, buttons):
        ...

    @abc.abstractmethod
    def _reply_photo(self, message, photo_bytes):
        ...

    @abc.abstractmethod
    def _reply_voice_file(self, message, voice_file):
        ...

    @abc.abstractmethod
    def _chat_action(self, message, action):
        ...

    @abc.abstractmethod
    def _transcribe_and_submit(self, message, audio_bytes):
        ...
