import json

from consts import CHAT_MODELS, REASONING_EFFORTS
from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsSettings(TelegramCommands):

    @command('Change the system message', 21)
    def system(self, message):
        new_system_message = self._get_command_argument(message, '/system')
        if not new_system_message:
            current_system_message = self.chat_manager.get_chat_for_message(message).get_current_system_message()
            self._reply(message,
                        f'The current system message is "{current_system_message}". '
                        f'Please enter the new system message or c to cancel.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.system
        else:
            if len(new_system_message) > 1:
                self.chat_manager.get_chat_for_message(message).set_system_message(new_system_message)

    @command('Select the model to use', 20)
    def model(self, message):
        current_model = self.chat_manager.get_chat_for_message(message).get_current_model()
        reply = f'Choose the new model (currently {current_model})'
        buttons = [[{
            'text': model,
            'callback_data': json.dumps({
                'cmd': 'model',
                'new_model': model
            }),
        }] for model in CHAT_MODELS]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('model')
    def model_callback(self, message, data):
        new_model = data['new_model']
        self.chat_manager.get_chat_for_message(message).set_model(new_model)

    @command('Select the reasoning effort', 22)
    def reasoning_effort(self, message):
        chat = self.chat_manager.get_chat_for_message(message)
        current_model = chat.get_current_model()
        if REASONING_EFFORTS not in CHAT_MODELS[current_model]:
            self._reply(message, 'The current model does not support reasoning effort selection')
            return
        current_reasoning_effort = chat.get_current_reasoning_effort()
        reply = f'Choose the new reasoning effort (currently {current_reasoning_effort})'
        buttons = [[{
            'text': effort,
            'callback_data': json.dumps({
                'cmd': 'reasoning_effort',
                'new_reasoning_effort': effort
            }),
        } for effort in CHAT_MODELS[current_model][REASONING_EFFORTS]]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('reasoning_effort')
    def reasoning_effort_callback(self, message, data):
        new_reasoning_effort = data['new_reasoning_effort']
        self.chat_manager.get_chat_for_message(message).set_reasoning_effort(new_reasoning_effort)
        self._reply(message, f'Changed reasoning effort to {new_reasoning_effort}.')

    @command('Select the vision detail to use', 80)
    def visiondetail(self, message):
        current_vision_detail = self.chat_manager.get_chat_for_message(message).get_current_vision_detail()
        reply = f'Choose the new vision detail (currently {current_vision_detail})'
        buttons = [[{
            'text': detail,
            'callback_data': json.dumps({
                'cmd': 'visiondetail',
                'new_vision_detail': detail
            }),
        } for detail in ['low', 'high', 'auto']]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('visiondetail')
    def visiondetail_callback(self, message, data):
        new_vision_detail = data['new_vision_detail']
        self.chat_manager.get_chat_for_message(message).set_vision_detail(new_vision_detail)
