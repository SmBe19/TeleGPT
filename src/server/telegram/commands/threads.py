import json

from server.telegram.command_manager import command, TelegramCommands, callback


class TelegramCommandsThreads(TelegramCommands):
    @command('Start a new conversation', 10)
    def new(self, message):
        template = self._get_command_argument(message, '/new')
        self.chatgpt_manager.get_chatgpt_for_message(message).new_thread(template or 'default')

    @command('Rename the current thread', 17)
    def rename(self, message):
        new_name = self._get_command_argument(message, '/rename')
        if not new_name:
            self._reply(message, 'Please enter the new thread name.')
            with self.user_manager.get_user_for_message(message) as user:
                user.open_command = self.rename
        else:
            self.chatgpt_manager.get_chatgpt_for_message(message).rename_thread(new_name)

    @command('Automatically name the current thread', 12)
    def autoname(self, message):
        self.chatgpt_manager.get_chatgpt_for_message(message).rename_thread_with_suggestion()

    @command('Finish the current thread', 18)
    def finish(self, message):
        self.chatgpt_manager.get_chatgpt_for_message(message).finish_thread()

    @command('Change the current thread', 11)
    def thread(self, message):
        chatgpt = self.chatgpt_manager.get_chatgpt_for_message(message)
        current_thread_id = chatgpt.get_current_thread_id()
        threads = chatgpt.get_thread_names()
        reply = f'The title of the current thread is "{threads[current_thread_id]}".' \
                f'\n\nSelect a thread to switch to.'
        buttons = [[{
            'text': threads[thread_id],
            'callback_data': json.dumps({
                'cmd': 'switch_thread',
                'new_thread_id': thread_id,
            }),
        }] for thread_id in threads]
        self._reply_keyboard(message, reply, self._with_cancel_button(buttons))

    @callback('switch_thread')
    def thread_callback(self, message, data):
        new_thread_id = data['new_thread_id']
        self.chatgpt_manager.get_chatgpt_for_message(message).switch_thread(new_thread_id)


    @command('Rewind user messages', 14)
    def rewind(self, message):
        amount = self._get_command_argument(message, '/rewind')
        try:
            amount = int(amount) if amount else 1
        except ValueError:
            amount = 1
        self.chatgpt_manager.get_chatgpt_for_message(message).rewind(amount)

    @command('Remind you of the last few messages', 13)
    def remindme(self, message):
        amount = self._get_command_argument(message, '/remindme')
        try:
            amount = int(amount) if amount else 1
        except ValueError:
            amount = 1
        self.chatgpt_manager.get_chatgpt_for_message(message).remindme(amount)
