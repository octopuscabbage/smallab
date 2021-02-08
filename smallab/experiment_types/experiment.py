import typing

import abc
import os

from smallab.smallab_types import Specification


class ExperimentBase(abc.ABC):
    def set_experiment_local_storage(self,experiment_local_storage_folder):
        """
        Called by ExperimentRunner to set up a folder for saving temporary data to file during an experiment, such as model weights
        :param folder:
        :return:
        """
        self.experiment_local_storage_folder = experiment_local_storage_folder
    def set_specification_local_storage(self, specification_local_storage_folder):
        self.specification_local_storage_folder = specification_local_storage_folder
    def get_specification_local_storage(self):
        """
        Returns the name of a folder to store extra data that pertains to a certain specification

        Folder is guarunteed to exist
        :param folder:
        :return:
        """
        os.makedirs(self.specification_local_storage_folder,exist_ok=True)
        return self.specification_local_storage_folder
    def get_experiment_local_storage(self):
        """
        Returns the name of a folder to store as a cache for all specifications using this experiment name
        :return:
        """
        os.makedirs(self.experiment_local_storage_folder, exist_ok=True)
        return self.experiment_local_storage_folder
    def set_logger_name(self, logger):
        """
        Called by ExperimentRunner to set a per-experiment logger
        :param logger: The logger which all logging in this experiment should be done to
        """
        self.logger = logger

    def get_logger_name(self):
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


class Experiment(ExperimentBase):
    """
    This represents the base class for what the user needs to implement.
    The main method takes a dictionary which is the specification and returns a dictionary which is the result.
    This is run by the ExperimentRunner class

    The lifecycle of this object is
    {} is called internally by smallab
    {.set_logging_folder() -> .get_logging_folder() -> .set_logger()} -> .main()
    """

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
