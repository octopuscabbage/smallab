import typing

import abc

from smallab.experiment_types.experiment import ExperimentBase
from smallab.smallab_types import Specification


class BaseHandler(abc.ABC):

    @abc.abstractmethod
    def run(self, experiment: ExperimentBase, name: typing.AnyStr, specification: Specification):
        pass
