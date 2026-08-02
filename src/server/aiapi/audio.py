import base64
import logging
import io
import os
import tempfile
import pydub
import requests

from openai import OpenAI

from server.aiapi.openrouter import OpenRouter

logger = logging.getLogger(__name__)


class AiAudio:

    def __init__(self):
        self.openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        self.openrouter = OpenRouter(api_key=os.environ['OPENROUTER_API_KEY'])
    
    def get_audio_bytes(self, url):
        with tempfile.TemporaryDirectory() as tempdir:
            response = requests.get(url)
            if not response.ok:
                logger.warning('Failed to download audio file')
                return None
            original_file = os.path.join(tempdir, 'voice')
            with open(original_file, 'wb') as f:
                f.write(response.content)
            destination_file = os.path.join(tempdir, 'voice.mp3')
            pydub.AudioSegment.from_file(original_file).export(destination_file, format='mp3')
            with open(destination_file, 'rb') as f:
                return f.read()

    def transcribe(self, audio_bytes, user):
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = 'voice.mp3'
        logger.info('Start transcribing')
        transcript = self.openrouter.stt(
            model=user.get_setting('transcribe_model'),
            audio_bytes_mp3=audio_bytes
        )
        logger.info('Finished transcribing')
        return transcript['text']

    def create_speech(self, message, user, callback):
        with tempfile.TemporaryDirectory() as tempdir:
            speech_model = user.get_setting('speech_model')
            # TODO ttsinstructions are not supported
            ttsinstructions = user.get_model_setting(speech_model, 'instructions')
            ttsvoice = user.get_model_setting(speech_model, 'voice')
            response = self.openrouter.tts(
                model=speech_model,
                input=message,
                voice=ttsvoice,
            )
            voice_file = os.path.join(tempdir, 'voice.mp3')
            with open(voice_file, 'wb') as f:
                f.write(response.content)
            callback(voice_file)
