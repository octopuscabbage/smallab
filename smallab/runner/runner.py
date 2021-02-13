import datetime
import json
import logging
import typing

import dill
import os

from smallab.callbacks import CallbackManager
from smallab.dashboard.dashboard import start_dashboard
from smallab.dashboard.dashboard_events import StartExperimentEvent, RegisterEvent, RegistrationCompleteEvent, \
    ProgressEvent
from smallab.experiment_naming import DiffNamer
from smallab.dashboard.utils import put_in_event_queue, LogToEventQueue
from smallab.experiment_types.checkpointed_experiment import IterativeExperiment
from smallab.experiment_types.experiment import ExperimentBase
from smallab.file_locations import (get_save_directory, get_experiment_save_directory)
from smallab.runner.runner_methods import run_and_save
from smallab.runner_implementations.abstract_runner import SimpleAbstractRunner, ComplexAbstractRunner
from smallab.runner_implementations.joblib_runner import JoblibRunner
from smallab.runner_implementations.multiprocessing_runner import MultiprocessingRunner
from smallab.smallab_types import Specification
from smallab.specification_hashing import specification_hash
from smallab.utilities.logging_callback import LoggingCallback


class ExperimentRunner(object):
    """
    The class which runs the batch of specifications.
    """

    def __init__(self):
        self.callbacks = [LoggingCallback()]
        self.logging_callback_attached = False

    def attach_callbacks(self, callbacks: typing.List[CallbackManager]):
        """
        Attach callback handlers to this runner object, will call them in order they are presented
        :return:
        """
        self.logging_callback_attached = False
        for callback in callbacks:
            if isinstance(callback, LoggingCallback):
                self.logging_callback_attached = True
        self.callbacks = callbacks

    def set_experiment_folder(self, folder: typing.AnyStr) -> typing.NoReturn:
        """
        Sets the folder where experiments will be stored
        defaults to "experiment_runs/"

        :param folder: A String folder path for the experiments
        :return: Nothing
        """
        self.experiment_folder = folder

    def _write_to_completed_json(self, name: typing.AnyStr, completed_specifications: typing.List[Specification],
                                 failed_specifications: typing.List[Specification]):
        """
        Writes out a file which shows the completed and failed specifications
        :param name: The name of the current batch
        :param completed_specifications:  Specifications which completed successfully
        :param failed_specifications:  Specifications which failed
        """
        with open(os.path.join(get_save_directory(name), "completed.json"), 'w') as f:
            json.dump(completed_specifications, f)
        with open(os.path.join(get_save_directory(name), "failed.json"), 'w') as f:
            json.dump(failed_specifications, f)

    def _find_uncompleted_specifications(self, name, specifications):
        already_completed_specifications = []
        for root, _, files in os.walk(get_experiment_save_directory(name)):
            for fname in files:
                if ".pkl" in fname:
                    with open(os.path.join(root, fname), "rb") as f:
                        completed = dill.load(f)
                    already_completed_specifications.append(completed["specification"])
                if ".json" in fname and fname != 'specification.json':
                    with open(os.path.join(root, fname), "r") as f:
                        completed = json.load(f)
                    already_completed_specifications.append(completed["specification"])

        need_to_run_specifications = []
        for specification in specifications:
            if specification in already_completed_specifications:
                logging.getLogger("smallab.runner").info("Skipping: " + str(specification))
            else:
                need_to_run_specifications.append(specification)
        return need_to_run_specifications

    def run(self, name: typing.AnyStr, specifications: typing.List[Specification], experiment: ExperimentBase,
            continue_from_last_run=True, propagate_exceptions=False,
            force_pickle=False, specification_runner: SimpleAbstractRunner = MultiprocessingRunner(),
            use_dashboard=True, context_type="fork", multiprocessing_lib=None, use_diff_namer=True) -> typing.NoReturn:

        """
        The method called to run an experiment
        :param propagate_exceptions: If True, exceptions won't be caught and logged as failed experiments but will cause the program to crash (like normal), useful for debugging exeperiments
        :param name: The name of this experiment batch
        :param specifications: The list of specifications to run. Should be a list of dictionaries. Each dictionary is passed to the experiment run method
        :param experiment: The experiment object to run
        :param continue_from_last_run: If true, will not redo already completed experiments. Defaults to true
        :param show_progress: Whether or not to show a progress bar for experiment completion
        :param force_pickle: If true, don't attempt to json serialze results and default to pickling
        :param specification_runner: An instance of ```AbstractRunner``` that will be used to run the specification
        :param use_dashboard: If true, use the terminal monitoring dashboard. If false, just stream logs to stdout.
        :return: No return
        """
        if use_diff_namer:
            diff_namer = DiffNamer(specifications)
        else:
            diff_namer = None
        self.diff_namer = diff_namer
        if multiprocessing_lib is None:
            import multiprocessing as mp
        else:
            mp = multiprocessing_lib
        ctx = mp.get_context(context_type)
        specification_runner.set_multiprocessing_context(ctx)
        if specification_runner is None:
            specification_runner = JoblibRunner(None)
        dashboard_process = None
        try:
            manager = ctx.Manager()
            eventQueue = manager.Queue(maxsize=2000)
            put_in_event_queue(eventQueue, StartExperimentEvent(name))
            # Set up root smallab logger
            folder_loc = os.path.join("experiment_runs", name, "logs", str(datetime.datetime.now()))
            file_loc = os.path.join(folder_loc, "main.log")
            if not os.path.exists(folder_loc):
                os.makedirs(folder_loc)
            logger = logging.getLogger("smallab")
            logger.propagate = False
            logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            # Can't do this with non-fork multiprocessing
            if context_type == "fork":
                fh = logging.FileHandler(file_loc)
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            if not use_dashboard:
                sh = logging.StreamHandler()
                sh.setFormatter(formatter)
                logger.addHandler(sh)
            else:
                #fq = LogToEventQueue(eventQueue)
                #sh = logging.StreamHandler(fq)
                #sh.setFormatter(formatter)
                #logging.getLogger("smallab").addHandler(sh)
                dashboard_process = ctx.Process(target=start_dashboard, args=(eventQueue, name,use_diff_namer))
                dashboard_process.start()
            experiment.set_logging_folder(folder_loc)

            self.force_pickle = force_pickle
            if not os.path.exists(get_save_directory(name)):
                os.makedirs(get_save_directory(name))

            if continue_from_last_run:
                need_to_run_specifications = self._find_uncompleted_specifications(name, specifications)
            else:
                need_to_run_specifications = specifications
            for callback in self.callbacks:
                callback.set_experiment_name(name)

            for specification in need_to_run_specifications:
                if diff_namer is not None:
                    specification_name = diff_namer.get_name(specification)
                else:
                    specification_name = specification_hash(specification)
                put_in_event_queue(eventQueue, RegisterEvent(specification_name, specification))
                if isinstance(experiment, IterativeExperiment):
                    put_in_event_queue(eventQueue, ProgressEvent(specification_name,0,experiment.max_iterations(specification)))

                
            put_in_event_queue(eventQueue, RegistrationCompleteEvent())

            if isinstance(specification_runner, SimpleAbstractRunner):
                specification_runner.run(need_to_run_specifications,
                                         lambda specification: run_and_save(name, experiment, specification,
                                                                            propagate_exceptions, self.callbacks,
                                                                            self.force_pickle, eventQueue, diff_namer))
            elif isinstance(specification_runner, ComplexAbstractRunner):
                specification_runner.run(need_to_run_specifications, name, experiment, propagate_exceptions,
                                         self.callbacks, self.force_pickle, eventQueue, diff_namer)

            self._write_to_completed_json(name, specification_runner.get_completed(),
                                          specification_runner.get_failed_specifications())

            # Call batch complete functions
            if specification_runner.get_exceptions() != []:
                for callback in self.callbacks:
                    callback.on_batch_failure(specification_runner.get_exceptions(),
                                              specification_runner.get_failed_specifications())

            if specification_runner.get_completed() != []:
                for callback in self.callbacks:
                    callback.on_batch_complete(specification_runner.get_completed())
        except Exception as e:
            logger = logging.getLogger("smallab")
            logger.error("Fatal Error",e)
        finally:
            if dashboard_process is not None:
                dashboard_process.terminate()
