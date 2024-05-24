import json

from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsWhisper(TelegramCommands):

    def __init__(self):
        super().__init__()
        self.whisper = None

    @command('Transform text to speech', 50)
    def tts(self, message):
        prompt = self._get_command_argument(message, '/tts')
        if not prompt:
            self._reply(message, 'Please enter the text to synthesize.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.tts
        else:
            with self.user_manager.get_user_for_message(message) as user:
                tts_model = user.tts_model
                tts_voice = user.tts_voice
            self.whisper.create_tts(prompt, tts_model, tts_voice, lambda f: self._reply_voice(message, f))

    @command('Select the tts model to use', 51)
    def ttsmodel(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            tts_model = user.tts_model
        reply = f'Choose tts model (currently {tts_model})'
        buttons = [[{
            'text': model,
            'callback_data': json.dumps({
                'cmd': 'ttsmodel',
                'new_model': model
            }),
        } for model in ['tts-1', 'tts-1-hd']]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('ttsmodel')
    def ttsmodel_callback(self, message, data):
        new_model = data['new_model']
        with self.user_manager.get_user_for_message(message) as user:
            user.tts_model = new_model
        self._reply(message, f'Changed tts model to {new_model}.')

    @command('Adjust tts voice', 52)
    def ttsvoice(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            tts_voice = user.tts_voice
        reply = f'Choose tts voice (currently {tts_voice})'
        buttons = [[{
            'text': voice,
            'callback_data': json.dumps({
                'cmd': 'ttsvoice',
                'voice': voice,
            }),
        } for voice in ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']]]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('ttsvoice')
    def ttsvoice_callback(self, message, data):
        new_voice = data['voice']
        with self.user_manager.get_user_for_message(message) as user:
            user.tts_voice = new_voice
        self._reply(message, f'Changed tts voice to {new_voice}.')

    @command('Switch creating tts for all assistant replies', 53)
    def ttsall(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            user.tts_all = not user.tts_all
            new_tts_all = user.tts_all
        if new_tts_all:
            self._reply(message, 'Changed setting. Will send tts for all assistant replies.')
        else:
            self._reply(message, 'Changed setting. Will not send tts for all assistant replies.')

