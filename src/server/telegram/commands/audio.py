import json

from consts import SPEECH_MODELS, SPEECH_VOICES, FEAT_SPEECH_INSTRUCTIONS
from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsAudio(TelegramCommands):

    def __init__(self):
        super().__init__()
        self.ai_audio = None

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
            self.ai_audio.create_tts(prompt, tts_model, tts_voice, lambda f: self._reply_voice(message, f))

    @command('Change instructions for tts', 51)
    def ttsinstructions(self, message):
        instructions = self._get_command_argument(message, '/ttsinstructions')
        with self.user_manager.get_user_for_message(message) as user:
            if not SPEECH_MODELS[user.speech_model].get(FEAT_SPEECH_INSTRUCTIONS, False):
                self._reply(message, 'The current model does not support instructions.')
                return
            if not instructions:
                old_instrcutions = user.speech_instructions[user.speech_model]
                if old_instrcutions:
                    self._reply(message, f'The current instructions are "{old_instrcutions}". Please enter the new instructions or r to reset or c to cancel.')
                else:
                    self._reply(message, 'Please enter the new instructions.')
                user.open_command = self.ttsinstructions
            else:
                if len(instructions) > 1:
                    user.speech_instructions[user.speech_model] = instructions
                elif instructions == 'r':
                    user.speech_instructions[user.speech_model] = None

    @command('Select the tts model to use', 52)
    def ttsmodel(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            speech_model = user.speech_model
        reply = f'Choose tts model (currently {speech_model})'
        buttons = [[{
            'text': model,
            'callback_data': json.dumps({
                'cmd': 'ttsmodel',
                'new_model': model
            }),
        }] for model in SPEECH_MODELS]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('ttsmodel')
    def ttsmodel_callback(self, message, data):
        new_model = data['new_model']
        with self.user_manager.get_user_for_message(message) as user:
            user.speech_model = new_model
        self._reply(message, f'Changed tts model to {new_model}.')

    @command('Adjust tts voice', 53)
    def ttsvoice(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            speech_voice = user.speech_voice[user.speech_model]
            voices = SPEECH_MODELS[user.speech_model][SPEECH_VOICES]
        reply = f'Choose tts voice (currently {speech_voice})'
        buttons = [[{
            'text': voice,
            'callback_data': json.dumps({
                'cmd': 'ttsvoice',
                'voice': voice,
            }),
        }] for voice in voices]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('ttsvoice')
    def ttsvoice_callback(self, message, data):
        new_voice = data['voice']
        with self.user_manager.get_user_for_message(message) as user:
            user.speech_voice[user.speech_model] = new_voice
        self._reply(message, f'Changed tts voice to {new_voice}.')

    @command('Switch creating tts for all assistant replies', 54)
    def ttsall(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            user.speech_all = not user.speech_all
            new_speech_all = user.speech_all
        if new_speech_all:
            self._reply(message, 'Changed setting. Will send tts for all assistant replies.')
        else:
            self._reply(message, 'Changed setting. Will not send tts for all assistant replies.')

