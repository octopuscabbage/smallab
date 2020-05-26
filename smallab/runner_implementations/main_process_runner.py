import logging
import typing

from tqdm import tqdm

from smallab.runner_implementations.abstract_runner import AbstractRunner
from smallab.smallab_types import Specification
from smallab.utilities.tqdm_to_logger import TqdmToLogger


class MainRunner(AbstractRunner):
    """
    The simplest runner which runs each specification in serial on the main process and thread.
    """

    def __init__(self, show_progress=True):
        super().__init__()
        self.show_progress = show_progress

    def run(self, specifications_to_run: typing.List[Specification], run_and_save_fn):
        completed_specifications = []
        failed_specifications = []
        exceptions = []
        for specification in tqdm(specifications_to_run,
                                  file=TqdmToLogger(logging.getLogger("smallab.main_process_runner")),
                                  desc="Experiments", disable=not self.show_progress):
            exception_thrown = run_and_save_fn(specification)

            if exception_thrown is None:
                completed_specifications.append(specification)
            else:
                failed_specifications.append(specification)
                exceptions.append(exception_thrown)
        self.finish(completed_specifications, failed_specifications, exceptions)
