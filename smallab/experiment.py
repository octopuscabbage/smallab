import abc
import typing


class Experiment(abc.ABC):

    @abc.abstractmethod
    def main(self, specification: typing.Dict) -> typing.Dict:
        pass
