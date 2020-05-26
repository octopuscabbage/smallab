import typing

import abc

from smallab.experiment_types.experiment import ExperimentBase
from smallab.smallab_types import Specification, ExpProgressTuple


class CheckpointedExperiment(ExperimentBase):
    """
    CheckpointedExperiment is an Experiment which can be stopped and restarted.
    Step is called multiple times, after it returns the current experiment is serialized allowing the experiment to
    restart seamlessly since to step it will not look any different whether python has shut down in between successive calls.
    Smallab will handle serialization and deserialization of this object.
    This will fail if objects attached to the experiment are not pickleable.

    The lifecycle of this object is

    {} is called internally by smallab, []* is called multiple times
    {.set_logging_folder() -> .get_logging_folder() -> .set_logger()} -> .initialize() -> [.step()]*
    """

    @abc.abstractmethod
    def initialize(self, specification: Specification):
        pass

    @abc.abstractmethod
    def step(self) -> typing.Union[ExpProgressTuple, typing.Dict]:
        """
        This method is to do work between checkpoints.
        Intermediate results should be saved to self
        :return: A tuple to indicate how much progress has been made if the experimetn is not done or  a dictionary of results when experiment has finished
        """
        pass
