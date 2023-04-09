import json
import logging
import os
import socketserver
import threading
import time
from logging.handlers import RotatingFileHandler
from multiprocessing.pool import ThreadPool

import dotenv

from consts import SOCKET_NAME, DATA_DIR
from server.telegram import Telegram

dotenv.load_dotenv('secrets.env')

logging.basicConfig(
    handlers=[RotatingFileHandler('telegpt.log', maxBytes=1000000, backupCount=10)],
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.DEBUG
)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(stream_handler)
logger = logging.getLogger(__name__)


def get_request_handler(telegram, thread_pool):
    class RequestHandler(socketserver.StreamRequestHandler):

        def handle(self):
            for line in self.rfile:
                if not line:
                    continue
                try:
                    data = json.loads(line.strip())
                except ValueError as e:
                    logger.warning('Invalid Request', exc_info=e)
                    continue
                if 'token' in data and 'update' in data:
                    thread_pool.apply_async(telegram.handle_update_safe, (data['update'], data['token']))

    return RequestHandler


class ThreadingServer(socketserver.UnixStreamServer, socketserver.ThreadingMixIn):
    pass


def setup_telegram():
    assert os.environ['TELEGRAM_TOKEN']
    assert os.environ['TELEGRAM_WEBHOOK']
    assert os.environ['ALLOWED_USERS']
    telegram = Telegram(
        bot_token=os.environ['TELEGRAM_TOKEN'],
        webhook=os.environ['TELEGRAM_WEBHOOK'],
        allowed_users=os.environ['ALLOWED_USERS'].split(',')
    )
    telegram.setup()
    os.makedirs(DATA_DIR, exist_ok=True)
    return telegram


def start_server(telegram, thread_pool):
    if os.path.exists(SOCKET_NAME):
        os.remove(SOCKET_NAME)
    server = ThreadingServer(SOCKET_NAME, get_request_handler(telegram, thread_pool))
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return server


def run_server():
    logger.info('Setup telegram')
    telegram = setup_telegram()

    logger.info('Start telegram webhook server')
    thread_pool = ThreadPool(processes=4)
    server = start_server(telegram, thread_pool)
    logger.info('Server started')

    try:
        while True:
            time.sleep(64)
    except KeyboardInterrupt:
        pass

    logger.info('Shutting down worker pool')
    thread_pool.close()
    thread_pool.join()
    logger.info('Shutting down server')
    server.shutdown()
    logger.info('Shutting down telegram')
    telegram.close()
    logger.info('Finished shutdown')
