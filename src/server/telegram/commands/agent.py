from server.telegram.command_manager import command, TelegramCommands


class TelegramCommandsAgent(TelegramCommands):

    @command('Use an agent to answer the prompt', 20)
    def agent(self, message):
        prompt = self._get_command_argument(message, '/agent')
        self.chatgpt_manager.get_chatgpt_for_message(message).agent(prompt)
