import base64
import logging
import io
import os
import requests

from openai import OpenAI

from consts import BASE64_JPEG_PREFIX, DEFAULT_OPENAI_IMAGE_SETTINGS, BASE64_PNG_PREFIX, OPENAI_IMAGE_SETTINGS, OPENAI_PREFIX, OPENAI_SETTING_PREFIX
from server.aiapi.openrouter import OpenRouter

logger = logging.getLogger(__name__)


class AiImages:

    def __init__(self):
        self.openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        self.openrouter = OpenRouter()

    def generate_image(self, prompt, user):
        image_model = user.get_setting('image_model')
        logger.info('Generate image with model %s and settings %s', image_model, user.get_model_settings(image_model))
        response = self.openrouter.image(
            model=image_model,
            prompt=prompt,
            **user.get_model_settings(image_model)
        )

        logger.info('Finished generating image')
        return base64.b64decode(response['data'][0]['b64_json'])
    
    def generate_image_edit(self, prompt, image_urls, user):
        image_model = user.get_setting('image_model')
        logger.info('Generate image edit with model %s based on %s images with settings %s', image_model, len(image_urls), user.get_model_settings(image_model))
        kwargs = {
            'model': user.get_setting('image_model')[len(OPENAI_PREFIX):],
            'n': 1,
        }
        for setting in OPENAI_IMAGE_SETTINGS.keys():
            kwargs[setting[len(OPENAI_SETTING_PREFIX):]] = user.get_model_setting(image_model, setting) or DEFAULT_OPENAI_IMAGE_SETTINGS[setting]
        # TODO replace this with requests call
        response = self.openai.images.edit(prompt=prompt, image=self._prepare_images(image_urls), **kwargs)
        logger.info('Finished generating image')
        return base64.b64decode(response.data[0].b64_json)
    
    def _prepare_images(self, image_urls):
        result = []
        for image in image_urls:
            found_bytes = None
            for prefix in [BASE64_PNG_PREFIX, BASE64_JPEG_PREFIX]:
                if image.startswith(prefix):
                    found_bytes = base64.b64decode(image[len(prefix):].strip())
                    break
            if not found_bytes:
                response = requests.get(image)
                if not response.ok:
                    logger.warning('Failed to download image file')
                    continue
                found_bytes = response.content
            result.append(io.BytesIO(found_bytes))
        for image in result:
            image.name = 'image.png'
        return result
