from server.telegram.command_manager import command, TelegramCommands


class TelegramCommandsGeneral(TelegramCommands):

    def start(self, message):
        username = message['from']['first_name']
        self._reply(
            message,
            f'Hi {username}, I am {self.assistant_name}, your personal assistant. How can I help you today?'
        )

    @command('Print help', 90)
    def help(self, message):
        # TODO write better help message
        self._reply(
            message,
            'Sorry, there is not a lot of help available just now. '
            'Check out the descriptions of the available commands.'
        )
