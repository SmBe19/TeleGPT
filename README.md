# TeleGPT
TeleGPT is an intelligent Telegram bot that uses OpenAI's GPT-3.5 language model to provide natural language-based interactions.

# Running
Install the python requirements (`requirements.txt`). Copy `secrets.template.env` to `secrets.env` and fill out the values. Set the `ALLOWED_USERS` value to a comma separated list of telegram account ids which should be allowed. An easy way to get this is to start the bot without any ids and trying to talk with the bot, it will print the required user id to the logs.

Start `./src/main.py server` and `./src/main.py frontend`. The server takes care of processing requests, making calls to the Telegram and OpenAI API. The frontend is solely responsible for accepting telegram webhook requests and forwarding them to the server.
