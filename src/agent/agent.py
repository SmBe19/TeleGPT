import datetime
import json
import logging
import re

from agent.tools.python import Python
from agent.tools.wikipedia import Wikipedia

INITIAL_PROMPT = '' \
                 'You are a friendly assistant.\n' \
                 'The current date is {date}.\n'

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
        messages = [
            {'role': 'system', 'content': INITIAL_PROMPT.format(date=datetime.datetime.now().strftime("%Y-%m-%d"))}
        ]
        if previous_messages is None:
            previous_messages = []
        for _ in range(limit):
            response = self._gpt(messages + previous_messages + [{'role': 'user', 'content': prompt}])
            messages.append(response)
            logger.info('Got response: %s', response)

            if not response.tool_calls:
                logger.info('Got final response')
                return response.content

            if response.content and update_notifier:
                update_notifier(response.content)

            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                logger.info('Found tool usage for tool %s', tool_name)
                logger.debug('Tool inputs for tool %s are:\n%s', tool_name, tool_call.function.arguments)
                if update_notifier:
                    update_notifier('[Use tool ' + tool_name + ' with arguments ' + tool_call.function.arguments + ']')

                tool = self.tools.get(tool_name)
                if not tool:
                    logger.warning("Tool %s not found", tool_name)
                    continue

                try:
                    arguments = json.loads(tool_call.function.arguments)
                except:
                    logger.warning("Input to tool %s is not valid json: %s", tool_name, tool_call.function.arguments)
                    messages.append({'role': 'tool', 'tool_call_id': tool_call.id, 'name': tool_name, 'content': 'Invalid json input, please try again'})
                    continue
                if not tool.validate_input(**arguments):
                    logger.warning("Input to tool %s is invalid: %s", tool_name, tool_call.function.arguments)
                    messages.append({'role': 'tool', 'tool_call_id': tool_call.id, 'name': tool_name, 'content': 'Invalid inputs, please try again'})
                    continue
                result = tool.process(**arguments)
                logger.info('Tool result: %s', result)
                messages.append({'role': 'tool', 'tool_call_id': tool_call.id, 'name': tool_name, 'content': tool.format_result(result, **arguments)})

        logger.warning('Did not find answer within %s steps, aborted', limit)
        return None

    def _gpt(self, messages):
        result = self.openai.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[{
                'type': 'function',
                'function': {
                    'name': tool_name,
                    'description': tool.description(),
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            key: {
                                'type': 'string',
                                'description': value
                            } for key, value in tool.parameters().items()
                        },
                        'required': list(tool.parameters().keys()),
                    }
                }
            } for tool_name, tool in self.tools.items()]
        )
        return result.choices[0].message
