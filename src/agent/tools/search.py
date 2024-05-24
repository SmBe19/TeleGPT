from agent.tools.tool import Tool


class Search(Tool):

    def description(self):
        return 'Search the internet for keywords.'

    def parameters(self):
        return {
            'keyword': 'The keyword to search.'
        }

    def validate_input(self, **kwargs):
        return 'keyword' in kwargs

    def process(self, **kwargs):
        print('Assistant wants to search for', kwargs['keyword'])
        answer = input('Please enter result: ')
        return answer

    def format_result(self, result, **kwargs):
        return result
