import ast
import logging

from agent.tools.timeout import run_with_time_limit
from agent.tools.tool import Tool

logger = logging.getLogger(__name__)

BLOCKED_BUILTIN_CALLS = {'open', 'eval', 'exec', 'input', 'breakpoint', 'compile', 'help', '__import__'}
ALLOWED_MODULE_IMPORTS = {'datetime', 'calendar', 'dateutil', 'random'}


class Python(Tool):

    def __init__(self, require_manual_approval=True):
        self.require_manual_approval = require_manual_approval

    def description(self):
        return 'Execute python code and get the result after execution. Cannot install any packages from pip.'

    def parameters(self):
        return {
            'code': 'The code to execute.'
        }

    def validate_input(self, **kwargs):
        return 'code' in kwargs

    def process(self, **kwargs):
        code = kwargs['code']
        logger.info('Assistant wants to execute the following code:\n%s', code)
        if not self._sanitize_code(code):
            logger.warning('Code execution was automatically blocked')
            return '<execution blocked>'
        if self.require_manual_approval:
            answer = input('Should I run this code? [y/N] ')
            if answer.lower() != 'y':
                logger.warning('Code execution blocked')
                return '<execution blocked>'
        return self._execute_code(code)

    def format_result(self, result, **kwargs):
        if isinstance(result, Exception):
            f'This code failed to run: {result}\nPlease fix the code and try again.'
        return result

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
        try:
            def run_code():
                env = {}
                # It's important that locals and globals are the same object
                exec(code, env, env)

            result = run_with_time_limit(30, run_code)
        except Exception as e:
            logger.warning('Code failed to run: %s', e)
            return e
        logger.info('Got the following result: %s', result)
        return result
