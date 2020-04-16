import json
import pickle

import os

import abc
import typing

from smallab.experiment import Experiment


class AbstractRunner(abc.ABC):
    def set_num_concurrency_to_use(self,num_cores):
        self.num_cores = num_cores

    def finish(self, completed_specifications: typing.List[typing.Dict],
               failed_specifications: typing.List[typing.Dict], exceptions: typing.List[Exception]):
        self.completed_specifications = completed_specifications
        self.failed_specifications = failed_specifications
        self.exceptions = exceptions

    @abc.abstractmethod
    def run(self, specifications_to_run: typing.List[typing.Dict],
            run_and_save_fn: typing.Callable[[typing.Dict], typing.Union[None, Exception]]):
        pass

    def get_completed(self):
        return self.completed_specifications

    def get_failed_specifications(self, ):
        return self.failed_specifications

    def get_exceptions(self):
        return self.exceptions
