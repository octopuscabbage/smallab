import datetime
import json
import logging
import pickle
import typing
from multiprocessing import cpu_count

import hashlib
import humanhash
import os
from copy import deepcopy

from smallab.callbacks import CallbackManager
from smallab.experiment import Experiment
from smallab.runner_implementations.abstract_runner import AbstractRunner
from smallab.runner_implementations.joblib_runner import JoblibRunner
from smallab.types import Specification
from smallab.utilities.logging_callback import LoggingCallback


def specification_hash(specification):
    return humanhash.humanize(hashlib.md5(json.dumps(specification, sort_keys=True).encode("utf-8")).hexdigest())


class ExperimentRunner(object):
    """
    The class which runs the batch of specifications.
    """

    def __init__(self):
        self.experiment_folder = "experiment_runs/"
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

    def get_save_directory(self, name: typing.AnyStr) -> typing.AnyStr:
        """
        Get the directory that the runs will be saved under
        :param name: The name of the current batch
        :return: The folder to save the runs under
        """
        return os.path.join(self.experiment_folder, name)

    def get_experiment_save_directory(self, name):
        return os.path.join(self.get_save_directory(name), "experiments")

    def get_pkl_file_location(self, name: typing.AnyStr, specification: typing.Dict) -> typing.AnyStr:
        """
        Get the filename to save the file under
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The filename to save this run under
        """
        return os.path.join(self.get_save_file_directory(name, specification),
                            str(hash(json.dumps(specification, sort_keys=True))) + ".pkl")

    def get_json_file_location(self, name, specification):
        return os.path.join(self.get_save_file_directory(name, specification),
                            str(hash(json.dumps(specification, sort_keys=True))) + ".json")

    def get_specification_file_location(self, name: typing.AnyStr, specification: typing.Dict) -> typing.AnyStr:
        """
        Get the specification file location
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The location where the specification.json should be saved
        """
        return os.path.join(self.get_save_file_directory(name, specification), "specification.json")

    def get_save_file_directory(self, name: typing.AnyStr, specification: Specification) -> typing.AnyStr:
        """
        Get the folder to save the .pkl file and specification.json file under
        :param name: The name of the current batch
        :param specification: The specification of the current run
        :return: The location where specification.json should be saved
        """
        return os.path.join(self.get_experiment_save_directory(name), specification_hash(specification))

    def _write_to_completed_json(self, name: typing.AnyStr, completed_specifications: typing.List[Specification],
                                 failed_specifications: typing.List[Specification]):
        """
        Writes out a file which shows the completed and failed specifications
        :param name: The name of the current batch
        :param completed_specifications:  Specifications which completed successfully
        :param failed_specifications:  Specifications which failed
        """
        with open(os.path.join(self.get_save_directory(name), "completed.json"), 'w') as f:
            json.dump(completed_specifications, f)
        with open(os.path.join(self.get_save_directory(name), "failed.json"), 'w') as f:
            json.dump(failed_specifications, f)

    def _find_uncompleted_specifications(self, name, specifications):
        already_completed_specifications = []
        for root, _, files in os.walk(self.get_experiment_save_directory(name)):
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

    def run(self, name: typing.AnyStr, specifications: typing.List[typing.Dict], experiment: Experiment,
            continue_from_last_run=True, num_parallel=1, show_progress=True, dont_catch_exceptions=False,
            force_pickle=False, specification_runner: AbstractRunner = JoblibRunner()) -> typing.NoReturn:
        """
        The method called to run an experiment
        :param name: The name of this experiment batch
        :param specifications: The list of specifications to run. Should be a list of dictionaries. Each dictionary is passed to the experiment run method
        :param experiment: The experiment object to run
        :param continue_from_last_run: If true, will not redo already completed experiments. Defaults to true
        :param num_parallel: The number of experiments to run in parallel. 1 is don't run in parallel. Defaults to 1. None is use all available.
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
        if not os.path.exists(self.get_save_directory(name)):
            os.makedirs(self.get_save_directory(name))

        if continue_from_last_run:
            need_to_run_specifications = self._find_uncompleted_specifications(name, specifications)
        else:
            need_to_run_specifications = specifications
        for callback in self.callbacks:
            callback.set_experiment_name(name)

        # Find the number of jobs to run
        if num_parallel is None:
            cores_to_use = min(cpu_count(), len(specifications))
        else:
            cores_to_use = min(num_parallel, len(specifications))
        specification_runner.set_num_concurrency_to_use(cores_to_use)

        specification_runner.run(need_to_run_specifications,
                                 lambda specification: self.__run_and_save(name, experiment, specification,
                                                                           dont_catch_exceptions))
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

    def __run_and_save(self, name, experiment, specification, dont_catch_exceptions):
        experiment = deepcopy(experiment)
        specification_id = specification_hash(specification)
        logger = logging.getLogger(f"smallab.experiment.{specification_id}")
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(f"{experiment.get_logging_folder()}/{specification_id}.log")
        # stream_handler = logging.StreamHandler()
        formatter = logging.Formatter(f"%(asctime)s [%(levelname)-5.5s]  %(message)s")
        # stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        experiment.set_logger(logger)

        def _interior_fn():
            result = experiment.main(specification)
            self._save_run(name,experiment, specification, result)
            for callback in self.callbacks:
                callback.on_specification_complete(specification, result)
            return None

        if not dont_catch_exceptions:
            try:
                _interior_fn()
            except Exception as e:
                for callback in self.callbacks:
                    callback.on_specification_failure(e, specification)
                return e
        else:
            _interior_fn()
            return None

    def _save_run(self, name, experiment,specification, result):
        os.makedirs(self.get_save_file_directory(name, specification))
        output_dictionary = {"specification": specification, "result": result}
        json_serialize_was_successful = False
        #Try json serialization
        if not self.force_pickle:
            json_filename = self.get_json_file_location(name, specification)
            try:
                with open(json_filename, "w") as f:
                    json.dump(output_dictionary, f)
                json_serialize_was_successful = True
            except Exception:
                experiment.get_logger().warning("Json serialization failed with exception",exc_info=True)
                os.remove(json_filename)
        #Try pickle serialization
        if self.force_pickle or not json_serialize_was_successful:
            pickle_file_location = self.get_pkl_file_location(name, specification)
            specification_file_location = self.get_specification_file_location(name, specification)
            try:
                with open(pickle_file_location, "wb") as f:
                    pickle.dump(output_dictionary, f)
                with open(specification_file_location, "w") as f:
                    json.dump(specification, f)
            except Exception:
                experiment.get_logger().critical("Experiment results serialization failed!!!",exc_info=True)
                os.remove(pickle_file_location)
                os.remove(specification_file_location)

