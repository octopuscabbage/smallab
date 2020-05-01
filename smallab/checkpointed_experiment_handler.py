import datetime
import logging
import pickle
import typing

import os
from dateutil.parser import parse

from smallab.experiment import CheckpointedExperiment
# TODO this should handle serializing a checkpointable experiment
from smallab.file_locations import get_partial_save_directory
from smallab.specification_hashing import specification_hash
from smallab.types import Specification


class CheckpointedExperimentHandler():
    """
    An internal handler to handle running checkpointed experiments.
    """
    def __init__(self, rolled_backups=3):
        """

        :param rolled_backups: Controls how many backups are kept. Once this limit is reached the oldest is deleted.
        """
        self.rolled_backups = rolled_backups

    def run(self, experiment: CheckpointedExperiment, name: typing.AnyStr, specification: Specification):
        try:
            experiment = self.load_most_recent(name,specification)
        except FileNotFoundError:
            experiment.initialize(specification)

        self.__save_checkpoint(experiment, name, specification)
        result = experiment.step()
        while result is None:
            self.__save_checkpoint(experiment, name, specification)
            result = experiment.step()
        return result

    def load_most_recent(self, name, specification):
        location = get_partial_save_directory(name, specification)
        checkpoints = self._get_time_sorted_checkpoints(name, specification)
        with open(os.path.join(location, str(checkpoints[-1]) + ".pkl"), "rb") as f:
            partial_experiment = pickle.load(f)
        return partial_experiment

    def _get_time_sorted_checkpoints(self, name, specification):

        location = get_partial_save_directory(name, specification)
        checkpoints = os.listdir(location)
        checkpoints = sorted(
            list(map(parse, map(lambda x: x.strip(".pkl"), checkpoints))))
        return checkpoints

    def __save_checkpoint(self, experiment, name, specification):
        try:
            location = get_partial_save_directory(name, specification)
            os.makedirs(location, exist_ok=True)
            with open(os.path.join(location, str(datetime.datetime.now()) + ".pkl"), "wb") as f:
                pickle.dump(experiment, f)
            logging.getLogger("smallab").info("Succesfully checkpointed {id}".format(id=specification_hash(specification)))
            checkpoints = os.listdir(location)
            if len(checkpoints) > self.rolled_backups:
                checkpoints = self._get_time_sorted_checkpoints(name, specification)
                os.remove(os.path.join(location, str(checkpoints[0]) + ".pkl"))
        except:
            logging.getLogger("smallab").warning("Unsuccesful at checkpointing {id}".format(id=specification_hash(specification)),
                                                 exc_info=True)
