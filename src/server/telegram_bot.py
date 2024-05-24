import json
import logging
import random
import string

import requests

from server.openai.dalle import DallE
from server.telegram.command_manager import telegram_commands, telegram_callbacks
from server.telegram.commands.agent import TelegramCommandsAgent
from server.telegram.commands.dalle import TelegramCommandsDalle
from server.telegram.commands.general import TelegramCommandsGeneral
from server.telegram.commands.gpt_settings import TelegramCommandsGptSettings
from server.telegram.commands.threads import TelegramCommandsThreads
from server.telegram.commands.whisper import TelegramCommandsWhisper
from server.telegram.gpt_manager import ChatGPTManager
from server.telegram.utils import UpdateDeduplicator, TelegramError
from server.telegram.user import TelegramUserManager
from server.openai.whisper import Whisper

logger = logging.getLogger(__name__)


class Telegram(
    TelegramCommandsGeneral,
    TelegramCommandsThreads,
    TelegramCommandsGptSettings,
    TelegramCommandsDalle,
    TelegramCommandsWhisper,
    TelegramCommandsAgent,
):

    def __init__(self, bot_token, webhook, allowed_users):
        super().__init__()
        self.bot_token = bot_token
        self.webhook = webhook
        self.allowed_users = set(int(x) for x in allowed_users)
        self.secret_token = ''.join(random.choice(string.ascii_letters) for _ in range(32))
        self.deduplicator = UpdateDeduplicator()
        self.chatgpt_manager = ChatGPTManager(self)
        self.dalle = DallE()
        self.whisper = Whisper()
        self.user_manager = TelegramUserManager(self)
        self.assistant_name = 'TeleGPT'

    def setup(self):
        self._post('setWebhook', url=self.webhook, allowed_updates=['message', 'callback_query'],
                   secret_token=self.secret_token)
        self._post(
            'setMyCommands',
            commands=[{'command': cmd, 'description': telegram_commands[cmd].__description__} for cmd in
                      sorted(telegram_commands, key=lambda cmd: (telegram_commands[cmd].__sort_order__, telegram_commands[cmd].__description__))]
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
            logger.info('Received message from user %s, chat %s', message['from']['id'], message['chat']['id'])
            self._handle_message(message)
        if 'callback_query' in update:
            telegram_callback = update['callback_query']
            self._post('answerCallbackQuery', callback_query_id=telegram_callback['id'])
            message = telegram_callback['message']
            if not self.user_manager.is_chat_known(message['chat']['id']):
                logger.info('Chat %s is not allowed to interact with bot, got callback query.', message['chat']['id'])
                return
            logger.info('Received callback for chat %s', message['chat']['id'])
            self._handle_callback(message, telegram_callback)

    def _post(self, endpoint, files=None, **data):
        if not data:
            data = {}
        if files:
            response = requests.post(f'https://api.telegram.org/bot{self.bot_token}/{endpoint}', data=data, files=files).json()
        else:
            response = requests.post(f'https://api.telegram.org/bot{self.bot_token}/{endpoint}', json=data).json()
        if not response['ok']:
            logger.error('Error calling Telegram API: %s', response['description'])
            raise TelegramError()
        return response['result']

    def _send_message(self, chatid, message, **kwargs):
        # TODO support parse_mode='MarkdownV2'
        return self._post('sendMessage', chat_id=chatid, text=message, **kwargs)

    def _send_photo(self, chatid, photo_url, **kwargs):
        return self._post('sendPhoto', chat_id=chatid, photo=photo_url, **kwargs)

    def _send_voice(self, chatid, voice_file, **kwargs):
        logging.info('Sending voice file %s to chat %s', voice_file, chatid)
        with open(voice_file, 'rb') as f:
            return self._post('sendVoice', chat_id=chatid, files={'voice': f}, **kwargs)

    def _reply(self, message, reply):
        return self._send_message(message['chat']['id'], reply)

    def _reply_keyboard(self, message, reply, buttons):
        return self._send_message(message['chat']['id'], reply, reply_markup={
            'inline_keyboard': buttons
        })

    def _reply_photo(self, message, photo_url):
        self._send_photo(message['chat']['id'], photo_url)

    def _reply_voice(self, message, voice_file):
        self._send_voice(message['chat']['id'], voice_file)

    def _chat_action(self, message, action):
        self._post('sendChatAction', chat_id=message['chat']['id'], action=action)

    def _update_reply(self, message, reply):
        return self._post('editMessageText', chat_id=message['chat']['id'], message_id=message['message_id'], text=message)

    def _update_reply_keyboard(self, message, buttons):
        reply_markup = {}
        if buttons:
            reply_markup = {'inline_keyboard': buttons}
        self._post('editMessageReplyMarkup', chat_id=message['chat']['id'], message_id=message['message_id'], reply_markup=reply_markup)

    def _handle_message(self, message):
        if 'text' in message:
            self._handle_text_message(message)
        elif 'audio' in message:
            self._handle_audio_message(message)
        elif 'voice' in message:
            self._handle_voice_message(message)

    def _handle_normal_message(self, message):
        self._chat_action(message, 'typing')
        self.chatgpt_manager.get_chatgpt_for_message(message).submit_message(message['text'])

    def _handle_audio_file(self, message, file_id):
        file_info = self._post('getFile', file_id=file_id)
        file_path = file_info['file_path']
        full_url = f'https://api.telegram.org/file/bot{self.bot_token}/{file_path}'
        transcript = self.whisper.transcribe_url(full_url)
        if not transcript:
            self._reply(message, 'Sorry, I did not understand this.')
            return
        self._reply(message, f'*Transcript*\n\n{transcript}')
        self._chat_action(message, 'typing')
        self.chatgpt_manager.get_chatgpt_for_message(message).submit_message(transcript)

    def _handle_text_message(self, message):
        logger.info('Handle text message')
        text = message['text']
        for entity in message.get('entities', []):
            if entity['type'] == 'bot_command':
                cmd = text[entity['offset'] + 1:entity['offset'] + entity['length']]
                cmd_func = telegram_commands.get(cmd)
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

    def _handle_audio_message(self, message):
        logger.info('Handle audio message')
        if message['audio']['file_size'] > 15 * 1024 * 1024:
            self._reply(message, 'Sorry, this file is too large.')
        self._handle_audio_file(message, message['audio']['file_id'])

    def _handle_voice_message(self, message):
        logger.info('Handle voice message')
        if message['voice']['file_size'] > 15 * 1024 * 1024:
            self._reply(message, 'Sorry, this file is too large.')
        self._handle_audio_file(message, message['voice']['file_id'])

    def _handle_callback(self, message, telegram_callback):
        data = json.loads(telegram_callback['data'])
        cmd = data['cmd']
        self._update_reply_keyboard(message, [])
        cmd_func = telegram_callbacks.get(cmd)
        if cmd_func:
            cmd_func(self, message, data)
        elif cmd == 'cancel':
            pass
        else:
            logger.warning('Unknown callback command %s', cmd)
