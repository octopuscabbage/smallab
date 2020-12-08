import typing

import abc

from smallab.callbacks import CallbackManager
from smallab.experiment_types.experiment import ExperimentBase
from smallab.smallab_types import Specification


class BaseAbstractRunner(abc.ABC):
    """
    The base class for all runner meta classes
    This should not be subclassed except by a meta runner class
    """
    def finish(self, completed_specifications: typing.List[Specification],
               failed_specifications: typing.List[Specification], exceptions: typing.List[Exception]):
        """
        Call in .run to save the results of the batch of specification

        It is assumed that the ith failed_specification and the ith exception are from the same experiment
        :param completed_specifications: Specifications that completed succesfully (returned None)
        :param failed_specifications: Specifications that failed  (retuned an Exception)
        :param exceptions: The exceptions corresponding to the failed exceptions
        :return:
        """
        self.completed_specifications = completed_specifications
        self.failed_specifications = failed_specifications
        self.exceptions = exceptions

    def get_completed(self):
        return self.completed_specifications

    def get_failed_specifications(self):
        return self.failed_specifications

    def get_exceptions(self):
        return self.exceptions

    def get_multiprocessing_context(self):
        return self.ctx

    def set_multiprocessing_context(self, ctx):
        self.ctx = ctx


class SimpleAbstractRunner(BaseAbstractRunner):
    """
    The base class for running a batch of specifications.

    The subclass must implement run and call finish after it is run.
    """

    @abc.abstractmethod
    def run(self, specifications_to_run: typing.List[Specification],
            run_and_save_fn: typing.Callable[[Specification], typing.Union[None, Exception]]):
        """
        The method to be implemented in concrete runner clases
        :param specifications_to_run: The list of specifications to run, all specifications should be run
        :param run_and_save_fn: The function to run and save the specifications, Each specification should have this function called on it. Returns None for a successful completion and Exception on failure.
        """
        pass


class ComplexAbstractRunner(BaseAbstractRunner):
    """
    A base class for running a batch of specifications that needs to manually call run_and_save and be passed all the arguments
    """

    @abc.abstractmethod
    def run(self, specifications_to_run: typing.List[Specification], experiment_name: typing.AnyStr,
            experiment: ExperimentBase,
            propagate_exceptions: bool, callbacks: typing.List[CallbackManager],
            force_pickle: bool, eventQueue, namer):
        pass
