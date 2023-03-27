import json
import logging
import os
import threading
import time
from queue import Queue, Empty

import openai

from consts import MAX_WORKER_IDLE_SECONDS, DATA_DIR, SYSTEM_MESSAGES, MESSAGES_UNTIL_AUTONAME

logger = logging.getLogger(__name__)


class ChatGPT:

    def __init__(self, user):
        self.user = user
        self.running = False
        self.last_update = 0
        self.running_lock = threading.Lock()
        self.queue = Queue()
        self.message_processing_thread = None
        self.data = {}
        self.current_thread = {}
        openai.api_key = os.environ['OPENAI_API_KEY']
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

    def submit_message(self, text):
        self.queue.put(lambda: self._process_message(text))

    def get_thread_names(self):
        return {thread_id: value['name'] for thread_id, value in
                sorted(self.data['threads'].items(), key=lambda x: x[0])}

    def new_thread(self):
        self.queue.put(lambda: self._new_thread())

    def rename_thread(self, new_name):
        self.queue.put(lambda: self._rename_thread(new_name))

    def rename_thread_with_suggestion(self):
        self.queue.put(lambda: self._suggest_thread_name())

    def switch_thread(self, new_thread_id):
        self.queue.put(lambda: self._switch_thread(new_thread_id))

    def finish_thread(self):
        self.queue.put(lambda: self._finish_thread())

    def rewind(self, amount):
        self.queue.put(lambda: self._rewind(amount))

    def remindme(self, amount):
        self.queue.put(lambda: self._remindme(amount))

    def set_system_message(self, message):
        self.queue.put(lambda: self._set_system_message(message))

    def get_current_system_message(self):
        for message in self.current_thread['messages']:
            if message['role'] == 'system':
                return message['content']
        return None

    def get_current_thread_id(self):
        return self.data['current_thread_id']

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
        root_data_path = os.path.join(DATA_DIR, f'{self.user.chatid}.json')
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
        return os.path.join(DATA_DIR, f'{self.user.chatid}_{thread_id}.json')

    def _save_current_thread(self):
        current_thread_id = self.get_current_thread_id()
        thread_data_path = self._thread_data_path(current_thread_id)
        with open(thread_data_path, 'w') as f:
            json.dump(self.current_thread, f)

    def _save_root_data(self):
        root_data_path = os.path.join(DATA_DIR, f'{self.user.chatid}.json')
        with open(root_data_path, 'w') as f:
            json.dump(self.data, f)

    def _suggest_thread_name(self, silent=False):
        logger.info('Ask ChatGPT for a thread name.')
        messages = [x for x in self.current_thread['messages']]
        messages.append({
            'role': 'user',
            'content': 'Title of our conversation? Only include the title.'
        })
        response = openai.ChatCompletion.create(
            model=self.current_thread['model'],
            messages=messages,
        )
        response = response['choices'][0]['message']['content']
        new_name = response.strip('"')
        old_name = self.data['threads'][self.get_current_thread_id()]['name']
        self.data['threads'][self.get_current_thread_id()]['name'] = new_name
        self._save_root_data()
        if not silent:
            self.user.send_message(f'Renamed thread "{old_name}" to "{new_name}".')

    def _process_message(self, message):
        logger.info('Send new message to ChatGPT.')
        # TODO deal with long threads, shortening them somehow
        self.current_thread['messages'].append({'role': 'user', 'content': message})
        response = openai.ChatCompletion.create(
            model=self.current_thread['model'],
            messages=self.current_thread['messages'],
        )
        logger.info('Got response from ChatGPT.')
        logger.debug('Usage for ChatGPT: %s tokens by chat %s', response['usage']['total_tokens'], self.user.chatid)
        self.current_thread['total_tokens'] += response['usage']['total_tokens']
        response_text = response['choices'][0]['message']['content']
        self.current_thread['messages'].append({'role': 'assistant', 'content': response_text})
        self._save_current_thread()
        self.user.send_message(response_text)
        if self.data['threads'][self.get_current_thread_id()]['name'] == 'Unnamed thread' and \
                len(self.current_thread['messages']) >= MESSAGES_UNTIL_AUTONAME * 2:
            self._suggest_thread_name(silent=True)

    def _new_thread(self, silent=False):
        thread_id = str(self.data['next_thread_id'])
        self.data['next_thread_id'] += 1
        self.data['threads'][thread_id] = {
            'name': 'Unnamed thread',
            'last_use': time.time(),
        }
        self.data['current_thread_id'] = thread_id
        self.current_thread = {
            'model': 'gpt-3.5-turbo',
            'total_tokens': 0,
            'messages': [
                {
                    'role': 'system',
                    'content': SYSTEM_MESSAGES['default'].format(assistant_name=self.user.telegram.assistant_name)
                }
            ]
        }
        self._save_current_thread()
        self._save_root_data()
        if not silent:
            self.user.send_message('Created new thread.')

    def _rename_thread(self, new_name):
        old_name = self.data['threads'][self.get_current_thread_id()]['name']
        self.data['threads'][self.get_current_thread_id()]['name'] = new_name
        self._save_root_data()
        self.user.send_message(f'Renamed thread "{old_name}" to "{new_name}".')

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

    def _rewind(self, amount):
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

    def _remindme(self, amount):
        messages = [x for x in self.current_thread['messages'] if x['role'] != 'system']
        start = max(0, len(messages) - amount)
        plural = 's' if len(messages) - start != 1 else ''
        self.user.send_message(f'The last {len(messages) - start} message{plural}:')
        for message in messages[start:]:
            author = 'You' if message['role'] == 'user' else self.user.telegram.assistant_name
            content = message['content']
            self.user.send_message(f'*{author}*:\n{content}')

    def _set_system_message(self, new_message):
        for message in self.current_thread['messages']:
            if message['role'] == 'system':
                message['content'] = new_message
                self.user.send_message('Updated system message.')
                return

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
            item()
            self.queue.task_done()
