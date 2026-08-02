import base64

from consts import BASE64_PREFIX, HIDDEN_IMAGE_SETTINGS, OPENAI_IMAGE_SETTINGS, OPENAI_PREFIX
from server.telegram.command_manager import CAT_IMAGES, command, callback
from server.telegram.commands.utils import TelegramCommandsUtils


class TelegramCommandsImages(TelegramCommandsUtils):

    def __init__(self):
        super().__init__()
        self.ai_images = None

    @command('Generate an image', CAT_IMAGES + 1)
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
                reply_message = self._reply_photo(message, photo_bytes)
                self._handle_photo_message(reply_message)

    @command('Generate an image edit', CAT_IMAGES + 2)
    def imgedit(self, message):
        image_model = self.user_manager.get_user_for_message(message).get_setting('image_model')
        if not image_model.startswith(OPENAI_PREFIX):
            self._reply(message, 'Sorry, this model does not support edits.')
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
                reply_message = self._reply_photo(message, photo_bytes)
                self._handle_photo_message(reply_message)

    @command('Select the image model to use', CAT_IMAGES + 3)
    def imgmodel(self, message):
        image_model = self.user_manager.get_user_for_message(message).get_setting('image_model')
        self._select_model('/imgmodel', 'imgmodel', 'image', image_model)(message)

    @callback('imgmodel')
    def imgmodel_callback(self, message, data):
        new_model = self.model_manager.short_ids[data['nm']]
        with self.user_manager.get_user_for_message(message) as user:
            user.set_setting('image_model', new_model)
        self._reply(message, f'Changed image model to {new_model}.')

    @command('Adjust image generation settings', CAT_IMAGES + 4)
    def imgsetting(self, message):
        image_model = self.user_manager.get_user_for_message(message).get_setting('image_model')
        setting_keys = [key for key in self.model_manager.models[image_model]['image_supported_parameters'].keys() if key not in HIDDEN_IMAGE_SETTINGS]
        if image_model.startswith(OPENAI_PREFIX):
            setting_keys.extend(OPENAI_IMAGE_SETTINGS.keys())
        self._set_enum_setting('imgcfg', None, setting_keys)(message)

    @callback('imgcfg')
    def imgsetting_callback(self, message, data):
        setting = data['nv']
        with self.user_manager.get_user_for_message(message) as user:
            image_model = user.get_setting('image_model')
            current_value = user.get_model_setting(image_model, setting)
            if image_model.startswith(OPENAI_PREFIX) and setting in OPENAI_IMAGE_SETTINGS:
                values = OPENAI_IMAGE_SETTINGS[setting]
            else:
                values = self.model_manager.models[image_model]['image_supported_parameters'][setting]
        self._set_enum_setting('imgcfgv', current_value, values, {'s': setting})(message)

    @callback('imgcfgv')
    def imgsettingvalue_callback(self, message, data):
        setting = data['s']
        new_value = data['nv']
        with self.user_manager.get_user_for_message(message) as user:
            image_model = user.get_setting('image_model')
            user.set_model_setting(image_model, setting, new_value)
        self._reply(message, f'Changed {setting} to {new_value}.')
