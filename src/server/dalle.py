import logging
import os

import openai

logger = logging.getLogger(__name__)


class DallE:

    def __init__(self):
        openai.api_key = os.environ['OPENAI_API_KEY']

    def generate_image(self, prompt, size):
        if str(size) not in ['256', '512', '1024']:
            logger.warning('Size %s is not supported for image generation, falling back to 256', size)
            size = '256'
        logger.info('Generate image of size %sx%s', size, size)
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            response_format='url',
            size=f'{size}x{size}',
        )
        return response['data'][0]['url']
