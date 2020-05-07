import typing

import abc

from smallab.smallab_types import Specification


class AbstractRunner(abc.ABC):
    """
    The base class for running a batch of specifications.

    The subclass must implement run and call finish after it is run.
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

    @abc.abstractmethod
    def run(self, specifications_to_run: typing.List[Specification],
            run_and_save_fn: typing.Callable[[Specification], typing.Union[None, Exception]]):
        """
        The method to be implemented in concrete runner clases
        :param specifications_to_run: The list of specifications to run, all specifications should be run
        :param run_and_save_fn: The function to run and save the specifications, Each specification should have this function called on it. Returns None for a successful completion and Exception on failure.
        """
        pass

    def get_completed(self):
        return self.completed_specifications

    def get_failed_specifications(self):
        return self.failed_specifications

    def get_exceptions(self):
        return self.exceptions
