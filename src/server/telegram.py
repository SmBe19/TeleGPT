import json
import logging
import random
import string
import threading
import time

import requests

from server.chatgpt import ChatGPT
from server.dalle import DallE

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


commands = {}


def command(description, order):
    def inner(f):
        f.__description__ = description
        f.__sort_order__ = order
        commands[f.__name__] = f
        return f

    return inner


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


class ChatGPTManager:

    def __init__(self, telegram):
        self.telegram = telegram
        self.lock = threading.Lock()
        self.chatgpt_instances = {}

    def get_chatgpt(self, chatid):
        with self.lock:
            if chatid not in self.chatgpt_instances or not self.chatgpt_instances[chatid].is_active():
                self.chatgpt_instances[chatid] = ChatGPT(self.telegram.user_manager.get_user(chatid))
                self.chatgpt_instances[chatid].start()
            return self.chatgpt_instances[chatid]

    def get_chatgpt_for_message(self, message):
        return self.get_chatgpt(message['chat']['id'])

    def close(self):
        for instance in self.chatgpt_instances.values():
            instance.close()


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
        self.dalle_size = '256'
        self.open_command = None

    def send_message(self, text):
        self.telegram._send_message(self.chatid, text)

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


class Telegram:

    def __init__(self, bot_token, webhook, allowed_users):
        self.bot_token = bot_token
        self.webhook = webhook
        self.allowed_users = set(int(x) for x in allowed_users)
        self.secret_token = ''.join(random.choice(string.ascii_letters) for _ in range(32))
        self.deduplicator = UpdateDeduplicator()
        self.chatgpt_manager = ChatGPTManager(self)
        self.dalle = DallE()
        self.user_manager = TelegramUserManager(self)
        self.assistant_name = 'TeleGPT'

    def setup(self):
        self._post('setWebhook', url=self.webhook, allowed_updates=['message', 'callback_query'],
                   secret_token=self.secret_token)
        self._post(
            'setMyCommands',
            commands=[{'command': cmd, 'description': commands[cmd].__description__} for cmd in
                      sorted(commands, key=lambda cmd: (commands[cmd].__sort_order__, commands[cmd].__description__))]
        )
        user_info = self._post('getMe')
        self.assistant_name = user_info['first_name']

    def close(self):
        self.chatgpt_manager.close()

    def handle_update_safe(self, update, secret_token):
        try:
            self.handle_update(update, secret_token)
        except Exception as e:
            logger.error('Telegram handler crashed', exc_info=e)

    def handle_update(self, update, secret_token):
        if secret_token != self.secret_token:
            logger.warning('Invalid secret token received.')
            return
        if self.deduplicator.deduplicate(update['update_id']):
            return
        if 'message' in update:
            message = update['message']
            if message['from']['id'] not in self.allowed_users:
                logger.info('User %s is not allowed to interact with bot.', message['from']['id'])
                self._reply(message, 'Sorry, I am not allowed to talk to you.')
                return
            # Make sure the user instance exists, is needed for authentication of callback_query
            self.user_manager.get_user_for_message(message)
            self._handle_message(message)
        if 'callback_query' in update:
            callback = update['callback_query']
            self._post('answerCallbackQuery', callback_query_id=callback['id'])
            message = callback['message']
            if not self.user_manager.is_chat_known(message['chat']['id']):
                logger.info('Chat %s is not allowed to interact with bot, got callback query.', message['chat']['id'])
                return
            self._handle_callback(message, callback)

    @command('Print help', 1)
    def help(self, message):
        # TODO write better help message
        self._reply(
            message,
            'Sorry, there is not a lot of help available just now. '
            'Check out the descriptions of the available commands.'
        )

    def start(self, message):
        username = message['from']['first_name']
        self._reply(
            message,
            f'Hi {username}, I am {self.assistant_name}, your personal assistant. How can I help you today?'
        )

    @command('Start a new conversation', 2)
    def new(self, message):
        self.chatgpt_manager.get_chatgpt_for_message(message).new_thread()

    @command('Rename the current thread', 3)
    def rename(self, message):
        new_name = self._get_command_argument(message, '/rename')
        if not new_name:
            self._reply(message, 'Please enter the new thread name.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.rename
        else:
            self.chatgpt_manager.get_chatgpt_for_message(message).rename_thread(new_name)

    @command('Automatically name the current thread', 4)
    def autoname(self, message):
        self.chatgpt_manager.get_chatgpt_for_message(message).rename_thread_with_suggestion()

    @command('Finish the current thread', 5)
    def finish(self, message):
        self.chatgpt_manager.get_chatgpt_for_message(message).finish_thread()

    @command('Rewind user messages', 6)
    def rewind(self, message):
        amount = self._get_command_argument(message, '/rewind')
        try:
            amount = int(amount) if amount else 1
        except ValueError:
            amount = 1
        self.chatgpt_manager.get_chatgpt_for_message(message).rewind(amount)

    @command('Remind you of the last few messages', 7)
    def remindme(self, message):
        amount = self._get_command_argument(message, '/remindme')
        try:
            amount = int(amount) if amount else 1
        except ValueError:
            amount = 1
        self.chatgpt_manager.get_chatgpt_for_message(message).remindme(amount)

    @command('Change the current thread', 8)
    def thread(self, message):
        chatgpt = self.chatgpt_manager.get_chatgpt_for_message(message)
        current_thread_id = chatgpt.get_current_thread_id()
        threads = chatgpt.get_thread_names()
        reply = f'The title of the current thread is "{threads[current_thread_id]}".' \
                f'\n\nSelect a thread to switch to.'
        buttons = [[{
            'text': threads[thread_id],
            'callback_data': json.dumps({
                'cmd': 'switch_thread',
                'new_thread_id': thread_id,
            }),
        }] for thread_id in threads]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @command('Generate an image with DALL·E', 20)
    def imagine(self, message):
        prompt = self._get_command_argument(message, '/imagine')
        if not prompt:
            self._reply(message, 'Please enter the image generation prompt.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.imagine
        else:
            with self.user_manager.get_user_for_message(message) as user:
                image_size = user.dalle_size
            image_url = self.dalle.generate_image(prompt, image_size)
            self._reply_photo(message, image_url)

    @command('Adjust image generation image size', 21)
    def imgsize(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_size = user.dalle_size
        reply = f'Choose image size (currently {image_size}x{image_size})'
        buttons = [[{
            'text': f'{size}x{size}',
            'callback_data': json.dumps({
                'cmd': 'imgsize',
                'size': size,
            }),
        } for size in ['256', '512', '1024']]]
        self._reply_keyboard(message, reply, buttons)

    def _get_command_argument(self, message, command_name):
        text = message['text']
        for entity in message.get('entities', []):
            if entity['type'] == 'bot_command':
                entity_end = entity['offset'] + entity['length']
                if text[entity['offset']:entity_end] == command_name:
                    return text[entity_end:].strip()
        return text

    def _post(self, endpoint, **data):
        if not data:
            data = {}
        response = requests.post(f'https://api.telegram.org/bot{self.bot_token}/{endpoint}', json=data).json()
        if not response['ok']:
            logger.error('Error calling Telegram API: %s', response['description'])
            raise TelegramError()
        return response['result']

    def _send_message(self, chatid, message, **kwargs):
        # TODO support parse_mode='MarkdownV2'
        return self._post('sendMessage', chat_id=chatid, text=message, **kwargs)

    def _update_message(self, chatid, message_id, message, **kwargs):
        # TODO support parse_mode='MarkdownV2'
        return self._post('editMessageText', chat_id=chatid, message_id=message_id, text=message, **kwargs)

    def _send_photo(self, chatid, photo_url, **kwargs):
        return self._post('sendPhoto', chat_id=chatid, photo=photo_url, **kwargs)

    def _reply(self, message, reply):
        return self._send_message(message['chat']['id'], reply)

    def _reply_keyboard(self, message, reply, buttons):
        return self._send_message(message['chat']['id'], reply, reply_markup={
            'inline_keyboard': buttons
        })

    def _reply_photo(self, message, photo_url):
        self._send_photo(message['chat']['id'], photo_url)

    def _update_reply(self, message, reply):
        return self._update_message(message['chat']['id'], message['message_id'], reply)

    def _update_reply_keyboard(self, message, reply, buttons):
        return self._update_message(message['chat']['id'], message['message_id'], reply, reply_markup={
            'inline_keyboard': buttons
        })

    def _with_cancel_button(self, buttons):
        return buttons + [[{
            'text': 'Cancel',
            'callback_data': json.dumps({
                'cmd': 'cancel',
            })
        }]]

    def _handle_message(self, message):
        text = message['text']
        for entity in message.get('entities', []):
            if entity['type'] == 'bot_command':
                cmd = text[entity['offset'] + 1:entity['offset'] + entity['length']]
                cmd_func = commands.get(cmd)
                if cmd_func:
                    cmd_func(self, message)
                    return
                elif cmd == 'start':
                    self.start(message)
                    return
                else:
                    logger.warning('Unknown bot command %s', cmd)
        open_command = None
        with self.user_manager.get_user_for_message(message) as user:
            if user.open_command:
                open_command = user.open_command
                user.open_command = None
        if open_command:
            open_command(message)
            return
        self._handle_normal_message(message)

    def _handle_normal_message(self, message):
        self.chatgpt_manager.get_chatgpt_for_message(message).submit_message(message['text'])

    def _handle_callback(self, message, callback):
        data = json.loads(callback['data'])
        cmd = data['cmd']
        self._update_reply(message, message['text'])
        if cmd == 'switch_thread':
            new_thread_id = data['new_thread_id']
            self.chatgpt_manager.get_chatgpt_for_message(message).switch_thread(new_thread_id)
        elif cmd == 'imgsize':
            new_size = data['size']
            with self.user_manager.get_user_for_message(message) as user:
                user.dalle_size = new_size
            self._reply(message, f'Changed size to {new_size}x{new_size}.')
