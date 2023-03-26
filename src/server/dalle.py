import os

import openai


class DallE:

    def __init__(self):
        openai.api_key = os.environ['OPENAI_API_KEY']

    def generate_image(self, prompt, size):
        if str(size) not in ['256', '512', '1024']:
            size = '256'
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            response_format='url',
            size=f'{size}x{size}',
        )
        return response['data'][0]['url']
