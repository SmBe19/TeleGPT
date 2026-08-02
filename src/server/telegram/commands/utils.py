from server.telegram.command_manager import TelegramCommands


class TelegramCommandsUtils(TelegramCommands):

    def _get_command_argument(self, message, command_name):
        text = message['text']
        for entity in message.get('entities', []):
            if entity['type'] == 'bot_command':
                entity_end = entity['offset'] + entity['length']
                if text[entity['offset']:entity_end] == command_name:
                    return text[entity_end:].strip()
        return text

    def _with_cancel_button(self, buttons):
        return buttons + [[{
            'text': 'Cancel',
            'callback_data': {
                'cmd': 'cancel',
            }
        }]]

    def _set_freetext_setting(self, command, callback, current_value):
        def freetext_setting_helper(message):
            new_value = self._get_command_argument(message, command)
            if not new_value:
                self._reply(message, f'The current value is "{current_value}". Please enter the new value or c to cancel.')
                with self.user_manager.get_user_for_message(message) as user:
                    user.open_command = freetext_setting_helper
            elif len(new_value) > 1:
                with self.user_manager.get_user_for_message(message) as user:
                    user.open_command = None
                self._reply(message, f'Changed value to "{new_value}".')
                callback(new_value)

    def _set_enum_setting(self, callback, current_value, available_values, extra_data=None):
        def enum_setting_helper(message):
            reply = f'Choose a new value (currently {current_value})' if current_value else 'Choose a new value'
            buttons = [[{
                'text': value,
                'callback_data': {
                    'cmd': callback,
                    'nv': value,
                    **(extra_data or {}),
                },
            }] for value in available_values]
            self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

        return enum_setting_helper

    def _select_model(self, command, callback, output_modality, current_model):
        def select_model_helper(message):
            model_search = self._get_command_argument(message, command)
            if not model_search:
                self._reply(message, f'The current model is "{current_model}". Please enter part of the new model name or c to cancel.')
                with self.user_manager.get_user_for_message(message) as user:
                    user.open_command = select_model_helper
            elif len(model_search) > 1:
                self.model_manager.reload_models()
                possible_models = self.model_manager.search_models(model_search, output_modality)
                if len(possible_models) not in range(1, 26):
                    if len(possible_models) == 0:
                        self._reply(message, f'No models found matching "{model_search}". Please try again or c to cancel.')
                    else:
                        self._reply(message, f'Too many models found matching "{model_search}" ({len(possible_models)}). Please try again or c to cancel.')
                    with self.user_manager.get_user_for_message(message) as user:
                        user.open_command = select_model_helper
                    return

                def build_model_label(model):
                    label = model['name']
                    prices = []
                    if model['pricing']['prompt'] > 0:
                        prices.append(f'in: ${model["pricing"]["prompt"]*1000000:.2f}')
                    if model['pricing']['completion'] > 0:
                        prices.append(f'out: ${model["pricing"]["completion"]*1000000:.2f}')
                    if prices:
                        label += f' ({", ".join(prices)})'
                    return label

                reply = f'Choose the new model (currently {current_model})'
                buttons = [[{
                    'text': build_model_label(model),
                    'callback_data': {
                        'cmd': callback,
                        'nm': model['short_id'],
                    },
                }] for model in possible_models]
                self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

        return select_model_helper
