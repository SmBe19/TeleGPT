from abc import ABC, abstractmethod


class Tool(ABC):

    @abstractmethod
    def description(self):
        pass

    @abstractmethod
    def parameters(self):
        pass

    @abstractmethod
    def validate_input(self, **kwargs):
        pass

    @abstractmethod
    def process(self, **kwargs):
        pass

    @abstractmethod
    def format_result(self, result, **kwargs):
        pass
