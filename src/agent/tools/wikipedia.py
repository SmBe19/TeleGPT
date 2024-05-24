import logging

import requests

from agent.tools.tool import Tool

logger = logging.getLogger(__name__)


class Wikipedia(Tool):

    def __init__(self, max_length=2048):
        self.searched_pages = set()
        self.searched_full_pages = set()
        self.search_redirects = {}
        self.max_length = max_length

    def description(self):
        return 'Retrieve Wikipedia articles.'

    def parameters(self):
        return {
            'article': 'The name of the article to retrieve.'
        }

    def validate_input(self, **kwargs):
        return 'article' in kwargs

    def process(self, perform_search=True, **kwargs):
        article = kwargs['article']
        logger.info('Going to search Wikipedia for "%s"', article)
        if article in self.searched_pages:
            self.searched_full_pages.add(article)
            if article in self.search_redirects:
                article = self.search_redirects[article]
            return self._limit_output(self._query_fullpage(article))
        self.searched_pages.add(article)
        result = self._limit_output(self._query_intro(article))
        if result is None and perform_search:
            logger.warning('Page does not exist, search Wikipedia instead.')
            search_result = self._search_page(article)
            logger.info('Search result: %s', search_result)
            if search_result is not None:
                return self.process(search_result, perform_search=False)
        return result

    def format_result(self, result, **kwargs):
        article = kwargs['article']
        if result is None:
            return 'This page does not exist.'
        result = ''
        if article in self.search_redirects:
            result += 'This page does not exist, instead I looked up the page "' + \
                      self.search_redirects[article] + '".\n'
        if article in self.searched_full_pages:
            return result + result
        return result + 'Here is the introduction of the Wikipedia article.\n' \
                        'Repeat the query to get the full article.\n' + result

    def _limit_output(self, text):
        if text is None:
            return text
        lines = text.splitlines()
        result = []
        total_length = 0
        for line in lines:
            total_length += len(line.split(' '))
            if total_length > self.max_length:
                return '\n'.join(result)
            result.append(line)
        return text

    def _query_wikipedia(self, params):
        result = requests.get('https://en.wikipedia.org/w/api.php', params=params).json()
        return result

    def _search_page(self, page):
        result = self._query_wikipedia({
            'format': 'json',
            'action': 'opensearch',
            'search': page,
            'limit': 1,
            'redirects': 'resolve',
        })
        fixed_name = result[1]
        if fixed_name:
            return fixed_name[0]
        return None

    def _query_intro(self, page):
        result = self._query_wikipedia({
            'format': 'json',
            'action': 'query',
            'prop': 'extracts',
            'titles': page,
            'redirects': 1,
            'exsectionformat': 'wiki',
            'explaintext': 1,
            'exlimit': 1,
            'exintro': 1
        })
        result_page = list(result['query']['pages'].values())[0]
        if 'missing' in result_page:
            logger.warning('Page "%s" does not exist', page)
            return None
        return result_page['extract']

    def _query_fullpage(self, page):
        result = self._query_wikipedia({
            'format': 'json',
            'action': 'query',
            'prop': 'extracts',
            'titles': page,
            'redirects': 1,
            'exsectionformat': 'wiki',
            'explaintext': 1,
        })
        result_page = list(result['query']['pages'].values())[0]
        if 'missing' in result_page:
            logger.warning('Page "%s" does not exist', page)
            return None
        return result_page['extract']
