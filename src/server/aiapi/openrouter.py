import base64
import os

import requests


class OpenRouter:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        self.base_url = 'https://openrouter.ai/api/v1'

    def _get(self, endpoint, params=None):
        response = requests.get(f'{self.base_url}/{endpoint}', headers={'Authorization': f'Bearer {self.api_key}'}, params=params)
        response.raise_for_status()
        return response.json()

    def _post_raw(self, endpoint, **data):
        response = requests.post(
            f'{self.base_url}/{endpoint}',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'X-OpenRouter-Title': 'TeleGPT',
            },
            json=data
        )
        response.raise_for_status()
        return response

    def _post(self, endpoint, **data):
        return self._post_raw(endpoint, **data).json()

    def chat(self, model, messages, **kwargs):
        return self._post(
            'chat/completions',
            model=model,
            messages=messages,
            **kwargs
        )

    def image(self, model, prompt, **kwargs):
        return self._post(
            'images',
            model=model,
            prompt=prompt,
            **kwargs
        )

    def tts(self, model, input, voice):
        kwargs = {}
        if voice:
            kwargs['voice'] = voice
        return self._post_raw(
            'audio/speech',
            model=model,
            input=input,
            response_format='mp3',
            **kwargs,
        )

    def stt(self, model, audio_bytes_mp3):
        return self._post(
            'audio/transcriptions',
            model=model,
            input_audio={
                'data': base64.b64encode(audio_bytes_mp3).decode(),
                'format': 'mp3'
            },
        )

    def models(self):
        return self._get('models?output_modalities=all')

    def image_models(self):
        return self._get('images/models')