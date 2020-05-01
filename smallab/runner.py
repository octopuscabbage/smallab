import datetime
import json
import logging
import pickle
import typing

import os
from copy import deepcopy

from smallab.callbacks import CallbackManager
from smallab.checkpointed_experiment_handler import CheckpointedExperimentHandler
from smallab.experiment import CheckpointedExperiment, BaseExperiment
from smallab.file_locations import (get_save_file_directory, get_json_file_location, get_pkl_file_location,
                                    get_specification_file_location, get_save_directory, get_experiment_save_directory,
                                    get_log_file)
from smallab.runner_implementations.abstract_runner import AbstractRunner
from smallab.runner_implementations.joblib_runner import JoblibRunner
from smallab.specification_hashing import specification_hash
from smallab.types import Specification
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
                        completed = pickle.load(f)
                    already_completed_specifications.append(completed["specification"])
                if ".json" in fname and fname != 'specification.json':
                    with open(os.path.join(root, fname), "r") as f:
                        completed = json.load(f)
                    already_completed_specifications.append(completed["specification"])

        need_to_run_specifications = []
        for specification in specifications:
            if specification in already_completed_specifications:
                logging.getLogger("smallab").info("Skipping: " + str(specification))
            else:
                need_to_run_specifications.append(specification)
        return need_to_run_specifications

    def run(self, name: typing.AnyStr, specifications: typing.List[Specification], experiment: BaseExperiment,
            continue_from_last_run=True, propagate_exceptions=False,
            force_pickle=False, specification_runner: AbstractRunner = JoblibRunner(None)) -> typing.NoReturn:
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
        :return: No return
        """
        # Set up root smallab logger
        folder_loc = os.path.join("experiment_runs", name, "logs", str(datetime.datetime.now()))
        file_loc = os.path.join(folder_loc, "main.log")
        if not os.path.exists(folder_loc):
            os.makedirs(folder_loc)
        logger = logging.getLogger("smallab")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh = logging.FileHandler(file_loc)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)
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

        specification_runner.run(need_to_run_specifications,
                                 lambda specification: self.__run_and_save(name, experiment, specification,
                                                                           propagate_exceptions))
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

    def __run_and_save(self, name, experiment, specification, propagate_exceptions):
        experiment = deepcopy(experiment)
        specification_id = specification_hash(specification)
        logger_name = "smallab.experiment.{specification_id}".format(specification_id=specification_id)
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(get_log_file(experiment, specification_id))
        # stream_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
        # stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        experiment.set_logger_name(logger_name)

        def _interior_fn():
            if isinstance(experiment, CheckpointedExperiment):
                result = CheckpointedExperimentHandler().run(experiment, name, specification)
            else:
                result = experiment.main(specification)
            self._save_run(name, experiment, specification, result)
            for callback in self.callbacks:
                callback.on_specification_complete(specification, result)
            return None

        if not propagate_exceptions:
            try:
                _interior_fn()
            except Exception as e:
                logger.error("Specification Failure", exc_info=True)
                for callback in self.callbacks:
                    callback.on_specification_failure(e, specification)
                return e
        else:
            _interior_fn()
            return None

    def _save_run(self, name, experiment, specification, result):
        os.makedirs(get_save_file_directory(name, specification))
        output_dictionary = {"specification": specification, "result": result}
        json_serialize_was_successful = False
        # Try json serialization
        if not self.force_pickle:
            json_filename = get_json_file_location(name, specification)
            try:
                with open(json_filename, "w") as f:
                    json.dump(output_dictionary, f)
                json_serialize_was_successful = True
            except Exception:
                experiment.get_logger_name().warning("Json serialization failed with exception", exc_info=True)
                os.remove(json_filename)
        # Try pickle serialization
        if self.force_pickle or not json_serialize_was_successful:
            pickle_file_location = get_pkl_file_location(name, specification)
            specification_file_location = get_specification_file_location(name, specification)
            try:
                with open(pickle_file_location, "wb") as f:
                    pickle.dump(output_dictionary, f)
                with open(specification_file_location, "w") as f:
                    json.dump(specification, f)
            except Exception:
                experiment.get_logger_name().critical("Experiment results serialization failed!!!", exc_info=True)
                os.remove(pickle_file_location)
                os.remove(specification_file_location)
