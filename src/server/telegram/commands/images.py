import base64
import json

from consts import IMAGE_MODELS, IMAGE_SIZES, IMAGE_QUALITY, IMAGE_STYLE, IMAGE_BACKGROUND, BASE64_PREFIX, FEAT_EDITS
from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsImages(TelegramCommands):

    def __init__(self):
        super().__init__()
        self.ai_images = None

    @command('Generate an image', 40)
    def imagine(self, message):
        prompt = self._get_command_argument(message, '/imagine')
        if not prompt:
            self._reply(message, 'Please enter the image generation prompt.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.imagine
        else:
            with self.user_manager.get_user_for_message(message) as user:
                self._chat_action(message, 'upload_photo')
                photo_bytes = self.ai_images.generate_image(prompt, user)
                self._reply_photo(message, photo_bytes)
            chat = self.chat_manager.get_chat_for_message(message)
            chat.submit_image_message(BASE64_PREFIX + base64.b64encode(photo_bytes).decode())

    @command('Generate an image edit', 41)
    def imgedit(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            if not IMAGE_MODELS[user.image_model].get(FEAT_EDITS, False):
                self.user.send_reply('Sorry, this model does not support edits.')
                return
        prompt = self._get_command_argument(message, '/imgedit')
        if not prompt:
            self._reply(message, 'Please enter the image generation prompt. Optionally, start with an integer to indicate how many of the last images should be included (default 1).')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.imgedit
        else:
            parts = prompt.split(' ', 1)
            imgcount = 1
            if parts[0].isdigit() and len(parts) > 1:
                imgcount = int(parts[0])
                prompt = parts[1]
            image_urls = []
            for cur_message in reversed(self.chat_manager.get_chat_for_message(message).get_image_messages()):
                for message_part in cur_message['content']:
                    if message_part.get('type') == 'image_url':
                        image_urls.append(message_part['image_url']['url'])
            image_urls = list(reversed(image_urls[:imgcount]))
            with self.user_manager.get_user_for_message(message) as user:
                self._chat_action(message, 'upload_photo')
                photo_bytes = self.ai_images.generate_image_edit(prompt, image_urls, user)
                self._reply_photo(message, photo_bytes)
            chat = self.chat_manager.get_chat_for_message(message)
            chat.submit_image_message(BASE64_PREFIX + base64.b64encode(photo_bytes).decode())

    @command('Select the image model to use', 42)
    def imgmodel(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_model = user.image_model
        reply = f'Choose image model (currently {image_model})'
        buttons = [[{
            'text': model,
            'callback_data': json.dumps({
                'cmd': 'imgmodel',
                'new_model': model
            }),
        }] for model in IMAGE_MODELS]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgmodel')
    def imgmodel_callback(self, message, data):
        new_model = data['new_model']
        with self.user_manager.get_user_for_message(message) as user:
            user.image_model = new_model
        self._reply(message, f'Changed image model to {new_model}.')

    @command('Adjust image generation image size', 43)
    def imgsize(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_size = user.image_size[user.image_model]
            available_image_sizes = IMAGE_MODELS[user.image_model][IMAGE_SIZES]
        reply = f'Choose image size (currently {image_size})'
        buttons = [[{
            'text': size,
            'callback_data': json.dumps({
                'cmd': 'imgsize',
                'size': size,
            }),
        } for size in available_image_sizes]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgsize')
    def imgsize_callback(self, message, data):
        new_size = data['size']
        with self.user_manager.get_user_for_message(message) as user:
            user.image_size[user.image_model] = new_size
        self._reply(message, f'Changed size to {new_size}.')

    @command('Adjust image generation quality', 44)
    def imgquality(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            if IMAGE_QUALITY not in IMAGE_MODELS[user.image_model]:
                self._reply(message, 'The current model does not support image quality')
                return
            image_quality = user.image_quality[user.image_model]
            available_qualities = IMAGE_MODELS[user.image_model][IMAGE_QUALITY]
        reply = f'Choose image quality (currently {image_quality})'
        buttons = [[{
            'text': quality,
            'callback_data': json.dumps({
                'cmd': 'imgquality',
                'quality': quality,
            }),
        } for quality in available_qualities]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgquality')
    def imgquality_callback(self, message, data):
        new_quality = data['quality']
        with self.user_manager.get_user_for_message(message) as user:
            user.image_quality[user.image_model] = new_quality
        self._reply(message, f'Changed quality to {new_quality}.')

    @command('Adjust image generation style', 45)
    def imgstyle(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            if IMAGE_STYLE not in IMAGE_MODELS[user.image_model]:
                self._reply(message, 'The current model does not support image styles')
                return
            image_style = user.image_style[user.image_model]
            available_styles = IMAGE_MODELS[user.image_model][IMAGE_STYLE]
        reply = f'Choose image style (currently {image_style})'
        buttons = [[{
            'text': style,
            'callback_data': json.dumps({
                'cmd': 'imgstyle',
                'style': style,
            }),
        } for style in available_styles]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgstyle')
    def imgstyle_callback(self, message, data):
        new_style = data['style']
        with self.user_manager.get_user_for_message(message) as user:
            user.image_style[user.image_model] = new_style
        self._reply(message, f'Changed style to {new_style}.')

    @command('Adjust image background style', 46)
    def imgbackground(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            if IMAGE_BACKGROUND not in IMAGE_MODELS[user.image_model]:
                self._reply(message, 'The current model does not support backgrounds')
                return
            image_background = user.image_style[user.image_model]
            available_backgrounds = IMAGE_MODELS[user.image_model][IMAGE_STYLE]
        reply = f'Choose image background style (currently {image_background})'
        buttons = [[{
            'text': style,
            'callback_data': json.dumps({
                'cmd': 'imgbackground',
                'style': style,
            }),
        } for style in available_backgrounds]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgbackground')
    def imgbackground_callback(self, message, data):
        new_style = data['style']
        with self.user_manager.get_user_for_message(message) as user:
            user.image_style[user.image_model] = new_style
        self._reply(message, f'Changed style to {new_style}.')

