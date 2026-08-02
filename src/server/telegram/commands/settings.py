from server.telegram.command_manager import CAT_ADVANCED, CAT_TEXT, command, callback
from server.telegram.commands.utils import TelegramCommandsUtils


class TelegramCommandsSettings(TelegramCommandsUtils):

    @command('Change the system message', CAT_TEXT + 2)
    def system(self, message):
        self._set_freetext_setting(message, '/system', self.chat_manager.get_chat_for_message(message).set_system_message, self.chat_manager.get_chat_for_message(message).get_current_system_message())(message)

    @command('Select the model to use', CAT_TEXT + 1)
    def model(self, message):
        current_model = self.chat_manager.get_chat_for_message(message).get_current_model()
        self._select_model('/model', 'model', 'text', current_model)(message)

    @callback('model')
    def model_callback(self, message, data):
        new_model = self.model_manager.short_ids[data['nm']]
        self.chat_manager.get_chat_for_message(message).set_model(new_model)

    @command('Toggle web search', CAT_TEXT + 3)
    def websearch(self, message):
        chat = self.chat_manager.get_chat_for_message(message)
        new_web_search = not chat.get_current_thread_setting('web_search')
        chat.set_thread_setting('web_search', new_web_search)

    @command('Select the reasoning effort', CAT_TEXT + 4)
    def reasoning_effort(self, message):
        chat = self.chat_manager.get_chat_for_message(message)
        reasoning_efforts = self.model_manager.models[chat.get_current_model()]['reasoning']['supported_efforts']
        if not reasoning_efforts:
            self._reply(message, 'The current model does not support reasoning effort selection')
            return
        current_reasoning_effort = chat.get_current_thread_setting('reasoning_effort')
        self._set_enum_setting('reasoning_effort', current_reasoning_effort, reasoning_efforts)(message)

    @callback('reasoning_effort')
    def reasoning_effort_callback(self, message, data):
        new_reasoning_effort = data['nv']
        self.chat_manager.get_chat_for_message(message).set_thread_setting('reasoning_effort', new_reasoning_effort)

    @command('Select the vision detail to use', CAT_ADVANCED + 2)
    def visiondetail(self, message):
        current_vision_detail = self.chat_manager.get_chat_for_message(message).get_current_thread_setting('vision_detail')
        self._set_enum_setting('visiondetail', current_vision_detail, ['low', 'high', 'original', 'auto'])(message)

    @callback('visiondetail')
    def visiondetail_callback(self, message, data):
        new_vision_detail = data['nv']
        self.chat_manager.get_chat_for_message(message).set_thread_setting('vision_detail', new_vision_detail)

    @command('Select the default model to use for new threads', CAT_ADVANCED + 3)
    def default_model(self, message):
        current_default_model = self.user_manager.get_user_for_message(message).get_setting('chat_model')
        self._select_model('/default_model', 'default_model', 'text', current_default_model)(message)

    @callback('default_model')
    def default_model_callback(self, message, data):
        new_default_model = self.model_manager.short_ids[data['nm']]
        with self.user_manager.get_user_for_message(message) as user:
            user.set_setting('chat_model', new_default_model)
        self._reply(message, f'Changed default model to {new_default_model}.')
