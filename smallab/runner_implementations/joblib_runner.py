import logging
import typing

from joblib import Parallel, delayed
from tqdm import tqdm

from smallab.runner_implementations.abstract_runner import SimpleAbstractRunner
from smallab.smallab_types import Specification
from smallab.utilities.tqdm_to_logger import TqdmToLogger


class JoblibRunner(SimpleAbstractRunner):
    """
    Runs the Specifications in parallel on threads using joblib
    """

    def __init__(self, num_parallel):
        self.num_parallel = num_parallel

    def run(self, specifications_to_run: typing.List[Specification],
            run_and_save_fn: typing.Callable[[Specification], typing.Union[None, Exception]]):
        completed_specifications = []
        failed_specifications = []
        exceptions = []

        exceptions_thrown = Parallel(n_jobs=self.num_parallel, prefer="threads")(
                delayed(lambda specification: run_and_save_fn(specification))(specification) for
                specification in specifications_to_run)

        # Look through output to create batch failures and sucesses
        for specification, exception_thrown in zip(specifications_to_run, exceptions_thrown):
            if exception_thrown is None:
                completed_specifications.append(specification)
            else:
                exceptions.append(exception_thrown)
                failed_specifications.append(specification)
        self.finish(completed_specifications, failed_specifications, exceptions)
