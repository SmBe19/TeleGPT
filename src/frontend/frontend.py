import json
import os
import socket
import sys

from flask import Flask, request

sys.path.append(os.path.abspath('src'))

from consts import SOCKET_NAME

app = Flask(__name__)


@app.route('/')
def index():
    return 'ok'


@app.route('/telegram/hook', methods=['POST'])
def telegram_hook():
    update = request.json
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    send_to_backend(update=update, token=secret_token)
    return ''


def send_to_backend(**data):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCKET_NAME)
    wfile = sock.makefile('wb')
    wfile.write((json.dumps(data) + '\n').encode())
    wfile.close()
    sock.close()
