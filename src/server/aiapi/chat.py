import base64
import datetime
import json
import logging
import os
import requests
import threading
import time
from queue import Queue, Empty

from consts import DEFAULT_THREAD_SETTINGS, MAX_WORKER_IDLE_SECONDS, DATA_DIR, SYSTEM_MESSAGE
from server.aiapi.openrouter import OpenRouter
from server.aiapi.utils import message_is_audio, message_is_image

logger = logging.getLogger(__name__)


class AiChat:

    def __init__(self, model_manager, user):
        self.model_manager = model_manager
        self.user = user
        self.running = False
        self.last_update = 0
        self.running_lock = threading.Lock()
        self.queue = Queue()
        self.message_processing_thread = None
        self.data = {}
        self.current_thread = {}
        self.openrouter = OpenRouter(api_key=os.environ['OPENROUTER_API_KEY'])
        self._load_data()

    def is_active(self):
        with self.running_lock:
            return self.running

    def start(self):
        with self.running_lock:
            self.last_update = time.time()
            self.message_processing_thread = threading.Thread(target=self._process_messages)
            self.message_processing_thread.daemon = True
            self.message_processing_thread.start()
            self.running = True

    def close(self):
        with self.running_lock:
            self.running = False
        self.message_processing_thread.join()
        self._save_current_thread()
        self._save_root_data()

    def submit_text_message(self, text):
        def _process_text_message():
            logger.info('Send new message to model.')
            self.current_thread['messages'].append({'role': 'user', 'content': text})
            messages = self.get_supported_messages()
            web_search = self.get_current_thread_setting('web_search')
            reasoning_effort = self.get_current_thread_setting('reasoning_effort')
            kwargs = {}
            if web_search:
                kwargs['plugins'] = [{ "id": "web" }]
            if reasoning_effort:
                kwargs['reasoning_effort'] = reasoning_effort
            response = self.openrouter.chat(
                model=self.get_current_model(),
                messages=messages,
                **kwargs,
            )
            if 'error' in response:
                logger.error('Error from model: %s', response)
                self.user.send_message(f'Error from model: {response["error"].get("message", "Unknown error")}')
                return
            total_tokens = response.get('usage', {}).get('total_tokens', 0)
            logger.info('Got response from model.')
            logger.debug('Usage for model: %s tokens by chat %s', total_tokens, self.user.chatid)
            self.current_thread['total_tokens'] += total_tokens
            response_message = response['choices'][0]['message']
            response_text = response_message['content']
            if response_message.get('audio'):
                logger.info('Response contains audio.')
                audio_bytes = base64.b64decode(response_message['audio']['data'])
                self.user.send_voice(audio_bytes)
            if response_message.get('images'):
                logger.info('Response contains image(s).')
                for image in response_message['images']:
                    image_bytes = requests.get(image['url']).content
                    self.user.send_photo(image_bytes)
            self.current_thread['messages'].append(response_message)
            self._save_current_thread()
            self.user.send_reply(response_text)
        self.queue.put(lambda: _process_text_message())

    def submit_image_message(self, image_url):
        def _process_image():
            logger.info('Add new image message to thread.')
            message = [{'type': 'image_url', 'image_url': {'url': image_url, 'detail': self.get_current_thread_setting('vision_detail')}}]
            self.current_thread['messages'].append({'role': 'user', 'content': message})
            self._save_current_thread()
        self.queue.put(lambda: _process_image())
    
    def submit_audio_message(self, audio_bytes):
        def _process_audio():
            logger.info('Add new audio message to thread.')
            message = [{'type': 'input_audio', 'input_audio': {'data': base64.b64encode(audio_bytes).decode(), 'format': 'mp3'}}]
            self.current_thread['messages'].append({'role': 'user', 'content': message})
            self._save_current_thread()
        self.queue.put(lambda: _process_audio())

    def get_thread_names(self):
        return {thread_id: value['name'] for thread_id, value in
                sorted(self.data['threads'].items(), key=lambda x: x[0])}

    def new_thread(self):
        self.queue.put(lambda: self._new_thread())

    def rename_thread(self, new_name):
        def _rename_thread():
            old_name = self.data['threads'][self.get_current_thread_id()]['name']
            self.data['threads'][self.get_current_thread_id()]['name'] = new_name
            self._save_root_data()
            self.user.send_message(f'Renamed thread "{old_name}" to "{new_name}".')
        self.queue.put(lambda: _rename_thread())

    def switch_thread(self, new_thread_id):
        self.queue.put(lambda: self._switch_thread(new_thread_id))

    def finish_thread(self):
        self.queue.put(lambda: self._finish_thread())

    def rewind(self, amount):
        def _rewind():
            messages = self.current_thread['messages']
            delete_from = len(messages)
            remaining_amount = amount
            for i in reversed(range(len(messages))):
                if messages[i]['role'] == 'user':
                    remaining_amount -= 1
                    delete_from = i
                    if remaining_amount == 0:
                        break
            self.current_thread['messages'] = messages[:delete_from]
            self._save_current_thread()
            self.user.send_message(f'Rewound {amount - remaining_amount} user messages.')
        self.queue.put(lambda: _rewind())

    def remindme(self, amount):
        def _remindme():
            messages = self.current_thread['messages']
            start = max(0, len(messages) - amount)
            plural = 's' if len(messages) - start != 1 else ''
            self.user.send_message(f'The last {len(messages) - start} message{plural}:')
            for message in messages[start:]:
                author = 'You' if message['role'] == 'user' else self.user.telegram.assistant_name
                content = message['content']
                if isinstance(content, str):
                    self.user.send_message(f'*{author}*:\n{content}')
                else:
                    self.user.send_message(f'*{author}*:\nBinary data')
        self.queue.put(lambda: _remindme())

    def set_system_message(self, message):
        def _set_system_message():
            self.current_thread['init_message'] = message
            self.user.send_message('Updated system message.')
        self.queue.put(lambda: _set_system_message())

    def set_model(self, model):
        def _set_model():
            model_details = self.model_manager.models[model]
            self.current_thread['model'] = model
            self.current_thread['reasoning_effort'] = model_details['reasoning']['default_effort']
            self.user.send_message(f'Changed model to {model_details["name"]} ({model}).')
            if self.current_thread['reasoning_effort']:
                self.user.send_message(f'Set reasoning effort to {self.current_thread["reasoning_effort"]}.')
            self.user.send_message(f'Supports {", ".join(model_details["architecture"]["input_modalities"])} as inputs, {", ".join(model_details["architecture"]["output_modalities"])} as outputs.')
        self.queue.put(lambda: _set_model())
    
    def get_current_thread_setting(self, setting):
        return self.current_thread.get(setting)

    def set_thread_setting(self, setting, value):
        def _set_thread_setting():
            self.current_thread[setting] = value
            self.user.send_message(f'Changed {setting} to {value}.')
        self.queue.put(lambda: _set_thread_setting())

    def get_current_system_message(self):
        return self.current_thread['init_message']

    def get_current_model(self):
        return self.current_thread['model']

    def get_current_thread_id(self):
        return self.data['current_thread_id']

    def get_all_messages(self, init_message=None):
        messages = [{
            'role': 'system',
            'content': init_message or self.current_thread['init_message']
        }]
        messages.extend(self.current_thread['messages'])
        return messages
    
    def get_supported_messages(self, init_message=None):
        model_details = self.model_manager.models[self.get_current_model()]
        vision = 'image' in model_details['architecture']['input_modalities']
        audio = 'audio' in model_details['architecture']['input_modalities']
        def _message_supported(message):
            return (vision or not message_is_image(message)) and (audio or not message_is_audio(message))
        return list(filter(_message_supported, self.get_all_messages(init_message)))
    
    def get_image_messages(self):
        return list(filter(message_is_image, self.get_all_messages()))
    
    def get_audio_messages(self):
        return list(filter(message_is_audio, self.get_all_messages()))

    def _load_current_thread(self):
        thread_data_path = self._thread_data_path(self.get_current_thread_id())
        if os.path.exists(thread_data_path):
            with open(thread_data_path) as f:
                self.current_thread = json.load(f)
        else:
            logger.warning('Could not load current thread with id %s for chat %s', self.get_current_thread_id(),
                           self.user.chatid)
            self._finish_thread()
            self._switch_to_latest_thread()

    def _load_data(self):
        root_data_path = os.path.join(DATA_DIR, f'{self.user.chatid}_chat.json')
        if os.path.exists(root_data_path):
            with open(root_data_path) as f:
                self.data = json.load(f)
            self._load_current_thread()
        else:
            self.data = {
                'current_thread_id': None,
                'next_thread_id': 0,
                'threads': {},
            }
            self._new_thread(silent=True)

    def _thread_data_path(self, thread_id):
        return os.path.join(DATA_DIR, f'{self.user.chatid}_thread_{thread_id}.json')

    def _save_current_thread(self):
        current_thread_id = self.get_current_thread_id()
        thread_data_path = self._thread_data_path(current_thread_id)
        with open(thread_data_path, 'w') as f:
            json.dump(self.current_thread, f)

    def _save_root_data(self):
        root_data_path = os.path.join(DATA_DIR, f'{self.user.chatid}_chat.json')
        with open(root_data_path, 'w') as f:
            json.dump(self.data, f)

    def _new_thread(self, silent=False):
        thread_id = str(self.data['next_thread_id'])
        self.data['next_thread_id'] += 1
        self.data['threads'][thread_id] = {
            'name': 'Unnamed thread ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_use': time.time(),
        }
        self.data['current_thread_id'] = thread_id
        default_model = self.user.get_setting('chat_model')
        model_details = self.model_manager.models[default_model]
        reasoning_effort = model_details['reasoning']['default_effort']
        self.current_thread = {
            **DEFAULT_THREAD_SETTINGS,
            'model': default_model,
            'reasoning_effort': reasoning_effort,
            'total_tokens': 0,
            'init_message': SYSTEM_MESSAGE.format(assistant_name=self.user.telegram.assistant_name),
            'messages': [],
        }
        self._save_current_thread()
        self._save_root_data()
        if not silent:
            self.user.send_message(f'Created new thread with model {default_model} ({reasoning_effort}).')

    def _switch_thread(self, new_thread_id):
        if new_thread_id in self.data['threads']:
            self.data['current_thread_id'] = new_thread_id
            self._load_current_thread()
            new_name = self.data['threads'][self.get_current_thread_id()]['name']
            self.data['threads'][self.get_current_thread_id()]['last_use'] = time.time()
            self._save_root_data()
            self.user.send_message(f'Switched to thread "{new_name}".')
        else:
            logger.warning('Encountered invalid thread id %s for chat %s without thread name', new_thread_id,
                           self.user.chatid)
            self.user.send_message('Error: unable to switch threads.')

    def _switch_to_latest_thread(self):
        if len(self.data['threads']) == 0:
            self._new_thread()
        else:
            latest = max(self.data['threads'].keys(), key=lambda x: self.data['threads'][x]['last_use'])
            self._switch_thread(latest)

    def _finish_thread(self):
        old_name = self.data['threads'][self.get_current_thread_id()]['name']
        thread_data_path = self._thread_data_path(self.get_current_thread_id())
        os.remove(thread_data_path)
        del self.data['threads'][self.get_current_thread_id()]
        self._save_root_data()
        self.user.send_message(f'Deleted thread "{old_name}".')
        self._switch_to_latest_thread()

    def _process_messages(self):
        while True:
            with self.running_lock:
                if not self.running:
                    return
            try:
                item = self.queue.get(timeout=5)
            except Empty:
                if time.time() - self.last_update > MAX_WORKER_IDLE_SECONDS:
                    with self.running_lock:
                        self.running = False
                        self.data = None
                        self.current_thread = None
                        return
                continue
            self.last_update = time.time()
            try:
                item()
            except Exception as e:
                logger.error('Model failed', exc_info=e)
                self.user.send_message('Sorry, I crashed. ' + str(e))
            self.queue.task_done()
