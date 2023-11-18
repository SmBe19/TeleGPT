import logging
import os
import tempfile

from openai import OpenAI
import pydub
import requests

logger = logging.getLogger(__name__)


class Whisper:

    def __init__(self):
        self.openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def transcribe_url(self, url):
        with tempfile.TemporaryDirectory() as tempdir:
            response = requests.get(url)
            if not response.ok:
                logger.warning('Failed to download file')
                return None
            original_file = os.path.join(tempdir, 'voice')
            with open(original_file, 'wb') as f:
                f.write(response.content)
            destination_file = os.path.join(tempdir, 'voice.mp3')
            pydub.AudioSegment.from_file(original_file).export(destination_file, format='mp3')
            logger.info('Start transcribing')
            with open(destination_file, 'rb') as f:
                transcript = self.openai.audio.transcriptions.create(file=f, model='whisper-1')
            logger.info('Finished transcribing')
            return transcript.text
