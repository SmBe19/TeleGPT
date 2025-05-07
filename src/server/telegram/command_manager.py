import abc
import json

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
    def _reply_voice(self, message, voice_file):
        ...

    @abc.abstractmethod
    def _chat_action(self, message, action):
        ...

    @abc.abstractmethod
    def _transcribe_and_submit(self, message, audio_bytes):
        ...

    def _get_command_argument(self, message, command_name):
        text = message['text']
        for entity in message.get('entities', []):
            if entity['type'] == 'bot_command':
                entity_end = entity['offset'] + entity['length']
                if text[entity['offset']:entity_end] == command_name:
                    return text[entity_end:].strip()
        return text

    def _with_cancel_button(self, buttons):
        return buttons + [[{
            'text': 'Cancel',
            'callback_data': json.dumps({
                'cmd': 'cancel',
            })
        }]]
