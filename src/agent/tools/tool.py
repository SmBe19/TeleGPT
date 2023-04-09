from abc import ABC, abstractmethod


class Tool(ABC):

    @abstractmethod
    def description(self):
        pass

    @abstractmethod
    def usage(self):
        pass

    @abstractmethod
    def examples(self):
        pass

    @abstractmethod
    def process(self, prompt):
        pass

    @abstractmethod
    def format_result(self, prompt, result):
        pass
