import datetime
import logging
import typing

import dill

from smallab.runner_implementations.abstract_runner import AbstractRunner
from smallab.smallab_types import Specification
from smallab.specification_hashing import specification_hash


def run_dill_encoded(payload):
    fun, args = dill.loads(payload)
    return fun(*args)


def apply_async(pool, fun, args):
    payload = dill.dumps((fun, args))
    return pool.apply_async(run_dill_encoded, (payload,))


def parallel_f(specification, run_and_save_fn, idx, max_num, counter, seconds_completion):
    alpha = .8
    specification_id = specification_hash(specification)
    logger = logging.getLogger("smallab.{id}.multiprocessing_runner".format(id=specification_id))
    time_str = "%d-%b-%Y (%H:%M:%S.%f)"
    beginning = datetime.datetime.now()
    beginning_string = beginning.strftime(time_str)
    logger.info("Begin job {idx} / {max_num} @ {beginning_string}".format(idx=idx, max_num=max_num,
                                                                          beginning_string=beginning_string))
    result = run_and_save_fn(specification)

    if not isinstance(result, Exception):
        end = datetime.datetime.now()
        end_str = end.strftime(time_str)
        time_to_complete = (end - beginning).total_seconds()
        if seconds_completion.get() == 0.0:
            seconds_completion.set(time_to_complete)
        else:
            seconds_completion.set(alpha * time_to_complete + (1 - alpha) * seconds_completion.get())
        completed_by = datetime.datetime.now() + datetime.timedelta(0, (
                max_num - counter.value) * seconds_completion.get())
        counter.value += 1
        logger.info(
            "Completed {counter}/{max_num} total @ {end_str} Taking {time_to_complete}. Estimated per job {seconds_completion}s. Estimate to complete @ {completed_by}.".format(
                counter=counter.value, max_num=max_num, end_str=end_str, time_to_complete=time_to_complete,
                seconds_completion=seconds_completion.get(), completed_by=completed_by))
    return result


class MultiprocessingRunner(AbstractRunner):
    """
    A runner which uses a multiprocessing pool to manage specification running
    """

    def __init__(self, mp_override=None, num_parallel=None):
        """
        :param mp_override: provide multiprocessing library that should be used. This is done because pytorch has a funky multiprocessing library that could be pased in here
        """
        if mp_override is not None:
            self.mp = mp_override
        else:
            import multiprocessing
            self.mp = multiprocessing
        self.num_parallel = None

    def run(self, specifications_to_run: typing.List[Specification],
            run_and_save_fn: typing.Callable[[Specification], typing.Union[None, Exception]]):
        pool = self.mp.Pool(self.num_parallel)
        manager = self.mp.Manager()
        counter = manager.Value('i', 0)
        seconds_completion = manager.Value("d", 0)

        def interior_fn(specification):
            return parallel_f(specification, run_and_save_fn, idx + 1, max_num, counter, seconds_completion)

        # listener.start()
        jobs = []
        max_num = len(specifications_to_run)
        for idx, specification in enumerate(specifications_to_run):
            jobs.append(apply_async(pool, interior_fn, (specification,)))
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
