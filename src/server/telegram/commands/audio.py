import base64

from server.telegram.command_manager import CAT_AUDIO, CAT_TRANSCRIBE, command, callback
from server.telegram.commands.utils import TelegramCommandsUtils


class TelegramCommandsAudio(TelegramCommandsUtils):

    def __init__(self):
        super().__init__()
        self.ai_audio = None

    @command('Transform text to speech', CAT_AUDIO + 1)
    def tts(self, message):
        prompt = self._get_command_argument(message, '/tts')
        if not prompt:
            self._reply(message, 'Please enter the text to synthesize.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.tts
        else:
            with self.user_manager.get_user_for_message(message) as user:
                self.ai_audio.create_speech(prompt, user, lambda f: self._reply_voice_file(message, f))

    @command('Change instructions for tts', CAT_AUDIO + 2)
    def ttsinstructions(self, message):
        self._set_freetext_setting(message, '/ttsinstructions', self.user_manager.get_user_for_message(message).get_setting('ttsinstructions'), lambda value: self.user_manager.get_user_for_message(message).set_setting('ttsinstructions', value))(message)

    @command('Select the tts model to use', CAT_AUDIO + 3)
    def ttsmodel(self, message):
        speech_model = self.user_manager.get_user_for_message(message).get_setting('speech_model')
        self._select_model('/ttsmodel', 'ttsmodel', 'speech', speech_model)(message)

    @callback('ttsmodel')
    def ttsmodel_callback(self, message, data):
        new_model = self.model_manager.short_ids[data['nm']]
        with self.user_manager.get_user_for_message(message) as user:
            user.set_setting('speech_model', new_model)
        self._reply(message, f'Changed tts model to {new_model}.')

    @command('Adjust tts voice', CAT_AUDIO + 4)
    def ttsvoice(self, message):
        speech_model = self.user_manager.get_user_for_message(message).get_setting('speech_model')
        voices = self.model_manager.models[speech_model]['supported_voices']
        if not voices:
            self._reply(message, 'The current model does not support voice selection')
            return
        current_voice = self.user_manager.get_user_for_message(message).get_model_setting(speech_model, 'voice')
        self._set_enum_setting('ttsvoice', current_voice, voices)(message)

    @callback('ttsvoice')
    def ttsvoice_callback(self, message, data):
        new_voice = data['nv']
        with self.user_manager.get_user_for_message(message) as user:
            speech_model = user.get_setting('speech_model')
            user.set_model_setting(speech_model, 'voice', new_voice)
        self._reply(message, f'Changed tts voice to {new_voice}.')

    @command('Switch creating tts for all assistant replies', CAT_AUDIO + 5)
    def ttsall(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            user.set_setting('speech_all', not user.get_setting('speech_all'))
            new_speech_all = user.get_setting('speech_all')
        if new_speech_all:
            self._reply(message, 'Changed setting. Will send tts for all assistant replies.')
        else:
            self._reply(message, 'Changed setting. Will not send tts for all assistant replies.')

    @command('Transcribe the last audio input', CAT_TRANSCRIBE + 1)
    def stt(self, message):
        audio_messages = self.chat_manager.get_chat_for_message(message).get_audio_messages()
        if not audio_messages:
            self._reply(message, 'Sorry, there is nothing to transcribe.')
            return
        for message_part in audio_messages[-1]['content']:
            if message_part.get('type') == 'input_audio':
                audio_bytes = base64.b64decode(message_part['input_audio']['data'])
                self._transcribe_and_submit(message, audio_bytes)
                return

    @command('Select the stt model to use', CAT_TRANSCRIBE + 2)
    def sttmodel(self, message):
        transcribe_model = self.user_manager.get_user_for_message(message).get_setting('transcribe_model')
        self._select_model('/sttmodel', 'sttmodel', 'transcription', transcribe_model)(message)

    @callback('sttmodel')
    def sttmodel_callback(self, message, data):
        new_model = self.model_manager.short_ids[data['nm']]
        with self.user_manager.get_user_for_message(message) as user:
            user.set_setting('transcribe_model', new_model)
        self._reply(message, f'Changed stt model to {new_model}.')

    @command('Switch transcribing for all audio inputs', CAT_TRANSCRIBE + 3)
    def sttall(self, message):
        with self.user_manager.get_user_for_message(message) as user:
            user.set_setting('transcribe_all', not user.get_setting('transcribe_all'))
            new_transcribe_all = user.get_setting('transcribe_all')
        if new_transcribe_all:
            self._reply(message, 'Changed setting. Will transcribe all audio inputs.')
        else:
            self._reply(message, 'Changed setting. Will not transcribe all audio inputs.')
