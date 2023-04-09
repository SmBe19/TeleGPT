#!/usr/bin/env python3
import argparse
import logging
import os
from logging.handlers import RotatingFileHandler

import dotenv
import openai

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv.load_dotenv('secrets.env')
openai.api_key = os.environ['OPENAI_API_KEY']

logging.basicConfig(
    handlers=[RotatingFileHandler('agent.log', maxBytes=1000000, backupCount=10)],
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.DEBUG
)


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = {
            logging.DEBUG: '\033[0m',  # white
            logging.INFO: '\033[94m',  # blue
            logging.WARNING: '\033[93m',  # yellow
            logging.ERROR: '\033[91m',  # red
            logging.CRITICAL: '\033[41m\033[37m'  # white on red bg
        }.get(record.levelno)
        return color + super().format(record) + '\033[0m'


stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(ColorFormatter('%(levelname)s - %(name)s - %(message)s'))
logging.getLogger().addHandler(stream_handler)
logger = logging.getLogger(__name__)


def main():
    from agent.agent import Agent

    parser = argparse.ArgumentParser()
    parser.add_argument('prompt', type=lambda s: s.strip(), nargs='+', help='Prompt message')
    args = parser.parse_args()
    prompt = ' '.join(args.prompt)

    agent = Agent()
    result = agent.process_prompt(prompt)
    print(result)


if __name__ == '__main__':
    main()
