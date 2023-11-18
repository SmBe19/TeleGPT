import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class DallE:

    def __init__(self):
        self.openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def generate_image_v2(self, prompt, size):
        if str(size) not in ['256x256', '512x512', '1024x1024']:
            logger.warning('Size %s is not supported for image generation, falling back to 256', size)
            size = '256x256'
        logger.info('Generate image of size %s', size)
        response = self.openai.images.generate(
            model='dall-e-2',
            prompt=prompt,
            n=1,
            response_format='url',
            size=size,
        )
        logger.info('Finished generating image')
        return response.data[0].url

    def generate_image_v3(self, prompt, size, quality, style):
        if str(size) not in ['1024x1024', '1792x1024', '1024x1792']:
            logger.warning('Size %s is not supported for image generation, falling back to 1024', size)
            size = '1024x1024'
        if quality not in ['standard', 'hd']:
            logger.warning('Quality %s is not supported for image generation, falling back to standard', quality)
            quality = 'standard'
        if style not in ['natural', 'vivid']:
            logger.warning('Quality %s is not supported for image generation, falling back to natural', style)
            style = 'natural'
        logger.info('Generate image of size %s', size)
        response = self.openai.images.generate(
            model='dall-e-3',
            prompt=prompt,
            n=1,
            response_format='url',
            size=size,
            quality=quality,
            style=style,
        )
        logger.info('Finished generating image')
        return response.data[0].url, response.data[0].revised_prompt
