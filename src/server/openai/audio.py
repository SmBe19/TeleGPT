import logging
import os
import tempfile

from openai import OpenAI
import pydub
import requests

logger = logging.getLogger(__name__)


class AiAudio:

    def __init__(self):
        self.openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def transcribe_url(self, url, user):
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
            logger.info('Start transcribing')
            with open(destination_file, 'rb') as f:
                transcript = self.openai.audio.transcriptions.create(file=f, model=user.transcribe_model)
            logger.info('Finished transcribing')
            return transcript.text

    def create_tts(self, message, user, callback):
        with tempfile.TemporaryDirectory() as tempdir:
            kwargs = {}
            if user.speech_instructions.get(user.speech_model):
                kwargs['instructions'] = user.speech_instructions[user.speech_model]
            response = self.openai.audio.speech.create(
                model=user.speech_model,
                input=message,
                voice=user.speech_voice[user.speech_model],
                response_format='opus',
                **kwargs,
            )
            voice_file = os.path.join(tempdir, 'voice.ogg')
            with open(voice_file, 'wb') as f:
                f.write(response.content)
            callback(voice_file)
