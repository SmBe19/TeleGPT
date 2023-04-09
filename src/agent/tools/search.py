from agent.tools.tool import Tool


class Search(Tool):

    def description(self):
        return 'Search the internet for keywords.'

    def usage(self):
        return 'Include [TOOL SEARCH]<keywords>[/TOOL] in your response and I will provide you ' \
               'with the results of this search.'

    def examples(self):
        return [
            '[TOOL SEARCH]Population Glasgow[/TOOL]',
            '[TOOL SEARCH]Election results France[/TOOL]'
        ]

    def process(self, prompt):
        print('Assistant wants to search for', prompt)
        answer = input('Please enter result: ')
        return answer

    def format_result(self, prompt, result):
        return prompt + '\nHere are the search results: ' + result
