import logging
import os
import time

from server.aiapi.openrouter import OpenRouter

logger = logging.getLogger(__name__)

class ModelManager:

    def __init__(self):
        self.models = {}
        self.short_ids = {}
        self._last_reload_time = 0
        self.openrouter = OpenRouter()
        self.reload_models()

    def reload_models(self):
        if len(self.models) > 0 and time.time() - self._last_reload_time < 60 * 60:
            logger.info('Skipping model reload, last reload was less than 60 minutes ago.')
            return

        models = self.openrouter.models()['data']
        self.models = {}
        current_id = 1
        for model in models:
            short_id = f'or-{current_id}'
            self.models[model['id']] = self._clean_model(model)
            self.models[model['id']]['short_id'] = short_id
            self.short_ids[short_id] = model['id']
            current_id += 1

        image_models = self.openrouter.image_models()['data']
        for model in image_models:
            self.models[model['id']]['image_supported_parameters'] = {
                key: model['supported_parameters'][key]['values'] for key in model['supported_parameters'].keys() if model['supported_parameters'][key]['type'] == 'enum'
            }
            self.models[model['id']]['image_supported_parameters_raw'] = model['supported_parameters']

        self._last_reload_time = time.time()
        logger.info(
            'Reloaded models from OpenRouter, found %d models (%d text, %d image, %d audio, %d speech, %d transcription, %d video).',
            len(self.models),
            self._count_models('text'),
            self._count_models('image'),
            self._count_models('audio'),
            self._count_models('speech'),
            self._count_models('transcription'),
            self._count_models('video')
        )

    def search_models(self, name, output_modality):
        search_parts = name.lower().split()
        results = []
        for model in self.models.values():
            if output_modality in model['architecture']['output_modalities']:
                if all(part in model['name'].lower() for part in search_parts):
                    results.append(model)
        return sorted(results, key=lambda m: m['name'])

    def _count_models(self, output_modality):
        return sum(1 for m in self.models.values() if output_modality in m['architecture']['output_modalities'])

    def _clean_model(self, model):
        return {
            'id': model['id'],
            'canonical_slug': model['canonical_slug'],
            'name': model['name'],
            'description': model['description'],
            'context_length': model['context_length'],
            'pricing': {
                'prompt': float(model['pricing']['prompt']),
                'completion': float(model['pricing']['completion']),
                'image': float(model['pricing'].get('image') or 0),
            },
            'architecture': {
                'input_modalities': model['architecture']['input_modalities'],
                'output_modalities': model['architecture']['output_modalities'],
            },
            'supported_parameters': model['supported_parameters'],
            'supported_voices': model['supported_voices'],
            'reasoning': {
                'supported_efforts': model['reasoning'].get('supported_efforts', []),
                'default_effort': model['reasoning'].get('default_effort'),
            } if model.get('reasoning') else {
                'supported_efforts': [],
                'default_effort': None,
            },
        }
