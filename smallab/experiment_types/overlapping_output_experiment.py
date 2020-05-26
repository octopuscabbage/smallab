import typing

import abc

from smallab.experiment_types.experiment import ExperimentBase
from smallab.smallab_types import Specification, ExpProgressTuple


class OverlappingOutputCheckpointedExperimentReturnValue():
    def __init__(self, should_continue: bool, specification: Specification, return_value: typing.Dict,
                 progress: typing.SupportsFloat, max_iterations: typing.SupportsFloat):
        """
        The holder class for output from an OverlappingOutputCheckpointedExperiment
        :param should_continue: True if the experiment needs to continue (to perform more iterations etc)
        :param specification: The specification this experiment will be saved under (not necessarily the specification passed to the experiment)
        :param return_value: The return value from this output
        :param progress: The progress (out of max_iterations)
        :param max_iterations: The maximum amount of iterations that will be run
        """
        self.should_continue = should_continue
        self.specification = specification
        self.return_value = return_value
        self.progress = progress
        self.max_iterations = max_iterations


class OverlappingOutputCheckpointedExperiment(ExperimentBase):
    """
    This experiment class handles the case where you have an experiment that you would like multiple overlapping experiments saved
    For example, you want to run your method for 100,200 and 300 iterations.
    This class allows you to save the 100 and 200 iteration experiments without restarting from scratch (for the 200 iteration experiment
    it would continue from the 100 iteration experiment)

    The experiment is also checkpointed between iterations you want to save like CheckpointedExperiment (and thus must
    also be picklable).
    """

    @abc.abstractmethod
    def initialize(self, specification: Specification):
        pass

    @abc.abstractmethod
    def step(self) -> typing.Union[ExpProgressTuple, OverlappingOutputCheckpointedExperimentReturnValue]:
        pass
