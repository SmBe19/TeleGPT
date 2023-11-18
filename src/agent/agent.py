import datetime
import logging
import re

from agent.tools.python import Python
from agent.tools.wikipedia import Wikipedia

INITIAL_PROMPT = '' \
                 'You are a friendly assistant.\n' \
                 'The current date is {date}.\n' \
                 'Knowledge data cuttoff date: 2021-09-01\n' \
                 'You have several tools at your disposal to complete your task.\n' \
                 'You do not need to ask for permission to use the tools.\n' \
                 'Always use a tool if you are not completely sure about the answer.\n' \
                 'When you use a tool, do not include any explanation. End your output after the tool usage.\n' \
                 'The available tools are described below.'

TOOL_SEARCH = re.compile(r'\[TOOL (?P<tool>[A-Z]+)](?P<arg>.*?)\[/TOOL]', re.DOTALL)
ALL_TOOLS = {
    'PYTHON': Python(require_manual_approval=False),
    # 'SEARCH': Search(),
    'WIKIPEDIA': Wikipedia()
}

logger = logging.getLogger(__name__)


class Agent:

    def __init__(self, openai, model, tools=None):
        self.openai = openai
        self.model = model
        self.tools = ALL_TOOLS if tools is None else tools

    def process_prompt(self, prompt, limit=4, previous_messages=None, update_notifier=None):
        logger.info('Start prompt "%s"', prompt)
        system_prompt = INITIAL_PROMPT.format(date=datetime.datetime.now().strftime("%Y-%m-%d"))
        for name, tool in self.tools.items():
            system_prompt += '\n\n# ' + name + \
                             '\nDescription: ' + tool.description() + \
                             '\nUsage: ' + tool.usage() + \
                             '\nExamples:\n' + '\n'.join(tool.examples())
        messages = [
            {'role': 'system', 'content': system_prompt}
        ]
        if previous_messages is None:
            previous_messages = []
        for _ in range(limit):
            response = self._gpt(messages + previous_messages + [{'role': 'user', 'content': prompt}])
            logger.info('Got response: %s', response)

            match = TOOL_SEARCH.search(response)
            if not match:
                logger.info('Got final response')
                return response

            logger.info('Found tool usage for tool %s', match.group('tool'))
            if update_notifier:
                update_notifier('[Use tool ' + match.group('tool') + ']')

            tool = self.tools.get(match.group('tool'))
            if not tool:
                logger.warning("Tool %s not found", match.group('tool'))
                messages.append({'role': 'system', 'content': 'The tool "' + match.group('tool') + '" does not exist.'})
                continue

            result = tool.process(match.group('arg'))
            logger.info('Tool result: %s', result)
            messages.append({'role': 'system', 'content': tool.format_result(match.group(), result)})

        logger.warning('Did not find answer within %s steps, aborted', limit)
        return None

    def _gpt(self, messages):
        result = self.openai.ChatCompletion.create(
            model=self.model,
            messages=messages
        )
        return result.choices[0].message.content
