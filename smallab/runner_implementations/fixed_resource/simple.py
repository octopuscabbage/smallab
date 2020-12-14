import queue
import typing

from copy import deepcopy

from smallab.callbacks import CallbackManager
from smallab.experiment_types.experiment import ExperimentBase
from smallab.runner.runner_methods import run_and_save
from smallab.runner_implementations.abstract_runner import ComplexAbstractRunner
from smallab.runner_implementations.multiprocessing_runner import apply_async
from smallab.smallab_types import Specification


def run(resource, name, experiment, specification, propagate_exceptions, callbacks, force_pickle, eventQueue,diff_namer):
    experiment_copy = deepcopy(experiment)
    experiment_copy.resource = resource
    return (specification, resource,
            run_and_save(name, experiment_copy, specification, propagate_exceptions, callbacks, force_pickle,
                         eventQueue,diff_namer))


class SimpleFixedResourceAllocatorRunner(ComplexAbstractRunner):
    '''
    This runner allocates one process per resource.
    Once a job completes the resource is freed and a new job can start with that resource
    This can be used to manage a fixed number of experiments per gpu that can run concurrently
    '''

    def __init__(self, resources: typing.List, mp_override=None):
        """
        :param mp_override: provide multiprocessing library that should be used. This is done because pytorch has a funky multiprocessing library that could be pased in here
        :param resources: an iterable of resources. if one job per gpu may look like [0,1,2,3]. If two jobs per gpu [(0,0),(0,1), (1,0),(1,1) ... ]
        """
        if mp_override is not None:
            self.mp = mp_override
        else:
            import multiprocessing
            self.mp = multiprocessing

        self.resources = resources

    def run(self, specifications_to_run: typing.List[Specification], experiment_name: typing.AnyStr,
            experiment: ExperimentBase, propagate_exceptions: bool, callbacks: typing.List[CallbackManager],
            force_pickle: bool, eventQueue,diff_namer):

        pool = self.get_multiprocessing_context().Pool(len(self.resources))
        specification_queue = deepcopy(specifications_to_run)
        free_resources = deepcopy(self.resources)
        active_jobs = []
        # initialize
        while free_resources != [] and specification_queue != []:
            resource = free_resources.pop()
            specification = specification_queue.pop()
            active_jobs.append(apply_async(pool, run, (
            resource, experiment_name, experiment, specification, propagate_exceptions, callbacks, force_pickle,
            eventQueue, diff_namer)))
        results = []
        # Poll and queue more resources
        while specification_queue != []:
            for job in active_jobs:
                if job.ready():
                    active_jobs.remove(job)
                    specification, resource, result = job.get()
                    results.append((specification, result))
                    free_resources.append(resource)
            while free_resources != [] and specification_queue != []:
                resource = free_resources.pop()
                if specification_queue != []:
                    specification = specification_queue.pop()
                    active_jobs.append(apply_async(pool, run, (
                        resource, experiment_name, experiment, specification, propagate_exceptions, callbacks,
                        force_pickle, eventQueue,diff_namer)))
            assert len(active_jobs) <= len(self.resources)
        #finish up all active jobs
        while active_jobs != []:
            for job in active_jobs:
                if job.ready():
                    active_jobs.remove(job)
                    specification,resource,result = job.get()
                    results.append((specification,result))
                    free_resources.append(resource)
        assert active_jobs == []
        assert specification_queue == []
        assert set(free_resources) == set(self.resources)
        completed_specifications = []
        exceptions = []
        failed_specifications = []
        for specification, exception_thrown in results:
            if exception_thrown is None:
                completed_specifications.append(specification)
            else:
                exceptions.append(exception_thrown)
                failed_specifications.append(specification)
        self.finish(completed_specifications, failed_specifications, exceptions)
