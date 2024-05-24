import json

from consts import GPT_MODELS
from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsGptSettings(TelegramCommands):

    @command('Change the system message', 15)
    def system(self, message):
        new_system_message = self._get_command_argument(message, '/system')
        if not new_system_message:
            current_system_message = self.chatgpt_manager.get_chatgpt_for_message(message).get_current_system_message()
            self._reply(message,
                        f'The current system message is "{current_system_message}". '
                        f'Please enter the new system message or c to cancel.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.system
        else:
            if len(new_system_message) > 1:
                self.chatgpt_manager.get_chatgpt_for_message(message).set_system_message(new_system_message)

    @command('Select the model to use', 16)
    def model(self, message):
        current_model = self.chatgpt_manager.get_chatgpt_for_message(message).get_current_model()
        reply = f'Choose the new model (currently {current_model})'
        buttons = [[{
            'text': model,
            'callback_data': json.dumps({
                'cmd': 'model',
                'new_model': model
            }),
        } for model in GPT_MODELS]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('model')
    def model_callback(self, message, data):
        new_model = data['new_model']
        self.chatgpt_manager.get_chatgpt_for_message(message).set_model(new_model)
