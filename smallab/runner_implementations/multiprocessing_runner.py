import datetime
import logging
import typing

import dill

from smallab.runner_implementations.abstract_runner import SimpleAbstractRunner
from smallab.smallab_types import Specification
from smallab.specification_hashing import specification_hash


def run_dill_encoded(payload):
    fun, args = dill.loads(payload)
    return fun(*args)


def apply_async(pool, fun, args):
    payload = dill.dumps((fun, args))
    return pool.apply_async(run_dill_encoded, (payload,))


class MultiprocessingRunner(SimpleAbstractRunner):
    """
    A runner which uses a multiprocessing pool to manage specification running
    """

    def __init__(self, num_parallel=None):
        """
        :param mp_override: provide multiprocessing library that should be used. This is done because pytorch has a funky multiprocessing library that could be pased in here
        """
        self.num_parallel = num_parallel

    def run(self, specifications_to_run: typing.List[Specification],
            run_and_save_fn: typing.Callable[[Specification], typing.Union[None, Exception]]):
        pool = self.get_multiprocessing_context().Pool(self.num_parallel)

        # listener.start()
        jobs = []
        for idx, specification in enumerate(specifications_to_run):
            jobs.append(apply_async(pool, run_and_save_fn, (specification,)))
        results = []
        for job in jobs:
            results.append(job.get())
        completed_specifications = []
        exceptions = []
        failed_specifications = []
        for specification, exception_thrown in zip(specifications_to_run, results):
            if exception_thrown is None:
                completed_specifications.append(specification)
            else:
                exceptions.append(exception_thrown)
                failed_specifications.append(specification)
        self.finish(completed_specifications, failed_specifications, exceptions)
