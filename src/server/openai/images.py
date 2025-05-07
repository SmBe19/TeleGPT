import base64
import logging
import io
import os
import requests

from openai import OpenAI

from consts import IMAGE_MODELS, FEAT_RESPONSE_FORMAT, FEAT_MODERATION, BASE64_PREFIX

logger = logging.getLogger(__name__)


class AiImages:

    def __init__(self):
        self.openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def generate_image(self, prompt, user):
        logger.info('Generate image of size %s with model %s', user.image_size[user.image_model], user.image_model)
        kwargs = self._get_common_args(user)
        if IMAGE_MODELS[user.image_model].get(FEAT_MODERATION, False):
            kwargs['moderation'] = 'low'
        response = self.openai.images.generate(prompt=prompt, **kwargs)
        logger.info('Finished generating image')
        return base64.b64decode(response.data[0].b64_json)
    
    def generate_image_edit(self, prompt, image_urls, user):
        logger.info('Generate image edit of size %s with model %s based on %s images', user.image_size[user.image_model], user.image_model, len(image_urls))
        kwargs = self._get_common_args(user)
        response = self.openai.images.edit(prompt=prompt, image=self._prepare_images(image_urls), **kwargs)
        logger.info('Finished generating image')
        return base64.b64decode(response.data[0].b64_json)
    
    def _get_common_args(self, user):
        kwargs = {
            'model': user.image_model,
            'n': 1,
            'size': user.image_size[user.image_model],
        }
        if user.image_model in user.image_quality:
            kwargs['quality'] = user.image_quality[user.image_model]
        if user.image_model in user.image_style:
            kwargs['style'] = user.image_style[user.image_model]
        if user.image_model in user.image_background:
            kwargs['background'] = user.image_background[user.image_model]
        if IMAGE_MODELS[user.image_model].get(FEAT_RESPONSE_FORMAT, False):
            kwargs['response_format'] = 'b64_json'
        return kwargs
    
    def _prepare_images(self, image_urls):
        result = []
        for image in image_urls:
            if image.startswith(BASE64_PREFIX):
                result.append(io.BytesIO(base64.b64decode(image[len(BASE64_PREFIX):])))
            else:
                response = requests.get(image)
                if not response.ok:
                    logger.warning('Failed to download image file')
                    continue
                result.append(io.BytesIO(response.content))
        for image in result:
            image.name = 'image.png'
        return result
