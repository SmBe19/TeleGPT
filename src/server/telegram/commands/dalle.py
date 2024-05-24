import json

from consts import DALLE_MODELS
from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsDalle(TelegramCommands):

    def __init__(self):
        super().__init__()
        self.dalle = None

    @command('Generate an image with DALL·E', 40)
    def imagine(self, message):
        prompt = self._get_command_argument(message, '/imagine')
        if not prompt:
            self._reply(message, 'Please enter the image generation prompt.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.imagine
        else:
            with self.user_manager.get_user_for_message(message) as user:
                image_model = user.dalle_model
                image_size = user.dalle_size()
                image_quality = user.dalle3_quality
                image_style = user.dalle3_style
                reply_prompt = user.dalle_prompt
                reply_imgurl = user.dalle_imgurl
            self._chat_action(message, 'upload_photo')
            if image_model == 'dall-e-2':
                image_url = self.dalle.generate_image_v2(prompt, image_size)
            elif image_model == 'dall-e-3':
                image_url, revised_prompt = self.dalle.generate_image_v3(prompt, image_size, image_quality, image_style)
                if reply_prompt:
                    self._reply(message, "The prompt might have been changed. The actual prompt used:")
                    self._reply(message, revised_prompt)
            else:
                raise ValueError()
            if reply_imgurl:
                self._reply(message, image_url)
            self._reply_photo(message, image_url)

    @command('Select the image model to use', 41)
    def imgmodel(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_model = user.dalle_model
        reply = f'Choose image model (currently {image_model})'
        buttons = [[{
            'text': model,
            'callback_data': json.dumps({
                'cmd': 'imgmodel',
                'new_model': model
            }),
        } for model in DALLE_MODELS]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgmodel')
    def imgmodel_callback(self, message, data):
        new_model = data['new_model']
        with self.user_manager.get_user_for_message(message) as user:
            user.dalle_model = new_model
        self._reply(message, f'Changed image model to {new_model}.')

    @command('Adjust image generation image size', 42)
    def imgsize(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_size = user.dalle_size()
            available_image_sizes = user.available_dalle_sizes()
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
            user.set_dalle_size(new_size)
        self._reply(message, f'Changed size to {new_size}.')

    @command('Adjust image generation quality', 43)
    def imgquality(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_quality = user.dalle3_quality
        reply = f'Choose image quality (currently {image_quality})'
        buttons = [[{
            'text': quality,
            'callback_data': json.dumps({
                'cmd': 'imgquality',
                'quality': quality,
            }),
        } for quality in ['standard', 'hd']]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgquality')
    def imgquality_callback(self, message, data):
        new_quality = data['quality']
        with self.user_manager.get_user_for_message(message) as user:
            user.dalle3_quality = new_quality
        self._reply(message, f'Changed quality to {new_quality}.')

    @command('Adjust image generation style', 44)
    def imgstyle(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            image_style = user.dalle3_style
        reply = f'Choose image quality (currently {image_style})'
        buttons = [[{
            'text': style,
            'callback_data': json.dumps({
                'cmd': 'imgstyle',
                'style': style,
            }),
        } for style in ['natural', 'vivid']]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('imgstyle')
    def imgstyle_callback(self, message, data):
        new_style = data['style']
        with self.user_manager.get_user_for_message(message) as user:
            user.dalle3_style = new_style
        self._reply(message, f'Changed style to {new_style}.')

    @command('Switch sending revised image prompts', 45)
    def imgprompt(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            user.dalle_prompt = not user.dalle_prompt
            new_prompt = user.dalle_prompt
        if new_prompt:
            self._reply(message, 'Changed setting. Will send revised image prompt.')
        else:
            self._reply(message, 'Changed setting. Will not send revised image prompt.')

    @command('Switch sending image url', 46)
    def imgurl(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            user.dalle_imgurl = not user.dalle_imgurl
            new_imgurl = user.dalle_imgurl
        if new_imgurl:
            self._reply(message, 'Changed setting. Will send image url.')
        else:
            self._reply(message, 'Changed setting. Will not send image url.')
