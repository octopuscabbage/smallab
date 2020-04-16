import abc
import typing


class Experiment(abc.ABC):
    def set_logger(self,logger):
        self.logger =logger
    def get_logger(self):
        return self.logger
    def set_logging_folder(self, folder_loc):
        self.logging_folder = folder_loc
    def get_logging_folder(self):
        return self.logging_folder

    @abc.abstractmethod
    def main(self, specification: typing.Dict) -> typing.Dict:
        pass

