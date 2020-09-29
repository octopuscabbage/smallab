import abc
import typing

from smallab.experiment_types.experiment import ExperimentBase
from smallab.smallab_types import Specification, ExpProgressTuple


class HasCheckpoint(abc.ABC):
    def __init__(self):
        self.steps_since_checkpoint = 0

    def steps_before_checkpoint(self) -> int:
        return 1

    def set_steps_since_checkpoint(self, steps_since_checkpoint: int):
        self.steps_since_checkpoint = steps_since_checkpoint

    def get_steps_since_checkpiont(self) -> int:
        return self.steps_since_checkpoint


class CheckpointedExperiment(ExperimentBase, HasCheckpoint):
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
