import ast
import logging
import sys
from io import StringIO

from agent.tools.timeout import time_limit
from agent.tools.tool import Tool

logger = logging.getLogger(__name__)

BLOCKED_BUILTIN_CALLS = {'open', 'eval', 'exec', 'input', 'breakpoint', 'compile', 'help', '__import__'}
ALLOWED_MODULE_IMPORTS = {'datetime', 'calendar', 'dateutil', 'random'}


class Python(Tool):

    def __init__(self, require_manual_approval=True):
        self.require_manual_approval = require_manual_approval

    def description(self):
        return 'Execute python code.'

    def usage(self):
        return 'Include [TOOL PYTHON]<code>[/TOOL] in your response and I will provide you ' \
               'with the result of the code after execution. I can not install anything from pip.'

    def examples(self):
        return [
            '[TOOL PYTHON]print(256*2)[/TOOL]',
            '[TOOL PYTHON]a = 5;b = 7; print(a**b)[/TOOL]'
        ]

    def process(self, prompt):
        logger.info('Assistant wants to execute the following code:\n%s', prompt)
        if not self._sanitize_code(prompt):
            logger.warning('Code execution was automatically blocked')
            return '<execution blocked>'
        if self.require_manual_approval:
            answer = input('Should I run this code? [y/N] ')
            if answer.lower() != 'y':
                logger.warning('Code execution blocked')
                return '<execution blocked>'
        return self._execute_code(prompt)

    def format_result(self, prompt, result):
        if isinstance(result, Exception):
            f'{prompt}\nThis code failed to run: {result}\nPlease fix the code and try again.'
        return f'{prompt}\nThe result of this code is {result}'

    def _is_allowed_module(self, module):
        logger.info('Check import for module %s', module)
        if module in ALLOWED_MODULE_IMPORTS:
            return True
        if '.' in module:
            return self._is_allowed_module(module[:module.rfind('.')])
        return False

    def _sanitize_code(self, code):
        tool_self = self

        class SanitizationVisitor(ast.NodeVisitor):
            error_msg = []

            def visit_Import(self, node):
                if all(tool_self._is_allowed_module(ast.unparse(x)) for x in node.names):
                    self.generic_visit(node)
                    return
                self.error_msg.append('Found import: ' + ast.unparse(node))

            def visit_ImportFrom(self, node):
                if tool_self._is_allowed_module(node.module):
                    self.generic_visit(node)
                    return
                self.error_msg.append('Found import: ' + ast.unparse(node))

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_BUILTIN_CALLS:
                    self.error_msg.append('Found blocked builtin: ' + ast.unparse(node))
                self.generic_visit(node)

        logger.info('Run code through sanitization')
        try:
            parsed = ast.parse(code)
        except SyntaxError as e:
            logger.warning('Code has a syntax error: %s', e)
            return False
        visitor = SanitizationVisitor()
        visitor.visit(parsed)
        if visitor.error_msg:
            logger.warning('Code failed sanitization: %s', visitor.error_msg)
            return False
        return True

    def _execute_code(self, code):
        logger.info('Going to execute the code')
        original_out = sys.stdout
        sys.stdout = buffer = StringIO()
        try:
            with time_limit(30):
                exec(code, {}, {})
        except Exception as e:
            logger.warning('Code failed to run: %s', e)
            return e
        sys.stdout = original_out
        result = buffer.getvalue().strip()
        logger.info('Got the following result: %s', result)
        return result
