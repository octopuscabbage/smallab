import typing

import abc

from smallab.types import Specification


class Experiment(abc.ABC):
    """
    This represents the base class for what the user needs to implement.
    The main method takes a dictionary which is the specification and returns a dictionary which is the result.
    This is run by the ExperimentRunner class
    """

    def set_logger(self, logger):
        """
        Called by ExperimentRunner to set a per-experiment logger
        :param logger: The logger which all logging in this experiment should be done to
        """
        self.logger = logger

    def get_logger(self):
        """
        Gets the logger that all logging in this experiment should be done to
        :return: An instance of logging.logger which corresponds to this experiment
        """
        return self.logger

    def set_logging_folder(self, folder_loc):
        """
        Set by ExperimentLogger, where the log files should go.
        :param folder_loc:
        :return:
        """
        self.logging_folder = folder_loc

    def get_logging_folder(self):
        """
        Read by ExperimentLogger, where the log files should go.
        :return:
        """
        return self.logging_folder

    @abc.abstractmethod
    def main(self, specification: Specification) -> typing.Dict:
        """
        The method that should be overriden when using smallab.
        Should contain the code for running your experiment.

        If an exception is raised the experiment is considered failed.

        :param specification: A dictionary passed which represents the variables of this experiment
        :return: A dictionary of results which will be serialized and saved if this experiment is succesful
        """
        pass
